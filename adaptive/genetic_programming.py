"""
Evolve mathematical alpha expressions via genetic programming
Uses DEAP library
"""
import random
import numpy as np
import operator
import pandas as pd
from typing import List, Callable, Tuple, Optional
from datetime import datetime, timedelta
from deap import base, creator, tools, gp
from utils.logger import setup_logger
from database.connection import db
from database.queries import Queries
from config.settings import settings

logger = setup_logger(__name__)

class GeneticProgramming:
    """Evolve alpha expressions for SentinelTrader"""
    
    def __init__(self, strategy: str):
        self.strategy = strategy
        self.toolbox: Optional[base.Toolbox] = None
        self.pset: Optional[gp.PrimitiveSet] = None
        self.best_expr: Optional[str] = None
        self._setup_toolbox()
    
    def _setup_toolbox(self):
        """Setup DEAP toolbox"""
        # Define primitives
        self.pset = gp.PrimitiveSet("MAIN", 4)
        self.pset.addPrimitive(np.add, 2)
        self.pset.addPrimitive(np.subtract, 2)
        self.pset.addPrimitive(np.multiply, 2)
        self.pset.addPrimitive(self._safe_divide, 2)
        self.pset.addPrimitive(np.abs, 1)
        self.pset.addPrimitive(np.sqrt, 1)
        self.pset.addPrimitive(np.tanh, 1)
        self.pset.addTerminal(1.0)
        self.pset.addTerminal(0.5)
        self.pset.addTerminal(2.0)
        
        self.pset.renameArguments(ARG0="close", ARG1="volume", ARG2="volatility", ARG3="momentum")
        
        # Define fitness and individual
        if not hasattr(creator, "FitnessMax"):
            creator.create("FitnessMax", base.Fitness, weights=(1.0,))
        if not hasattr(creator, "Individual"):
            creator.create("Individual", gp.PrimitiveTree, fitness=creator.FitnessMax)
        
        # Setup toolbox
        self.toolbox = base.Toolbox()
        self.toolbox.register("expr", gp.genHalfAndHalf, pset=self.pset, min_=1, max_=3)
        self.toolbox.register("individual", tools.initIterate, creator.Individual, self.toolbox.expr)
        self.toolbox.register("population", tools.initRepeat, list, self.toolbox.individual)
        
        self.toolbox.register("compile", gp.compile, pset=self.pset)
        self.toolbox.register("evaluate", self._evaluate)
        self.toolbox.register("select", tools.selTournament, tournsize=3)
        self.toolbox.register("mate", gp.cxOnePoint)
        self.toolbox.register("expr_mut", gp.genHalfAndHalf, min_=0, max_=2)
        self.toolbox.register("mutate", gp.mutUniform, expr=self.toolbox.expr_mut)
        
        self.toolbox.decorate("mate", gp.staticLimit(key=operator.attrgetter("height"), max_value=17))
        self.toolbox.decorate("mutate", gp.staticLimit(key=operator.attrgetter("height"), max_value=17))
    
    @staticmethod
    def _safe_divide(a, b):
        """Safe division"""
        return np.where(b != 0, a / b, 0)
    
    def _evaluate(self, individual, data: pd.DataFrame) -> Tuple[float,]:
        """Evaluate expression fitness (ICIR)"""
        try:
            func = self.toolbox.compile(individual)
            
            # Calculate alpha signal
            alpha = func(
                data["close"].values,
                data["volume"].values,
                data["volatility"].values,
                data["momentum"].values
            )
            
            # Calculate ICIR
            icir = self._calculate_icir(alpha, data["returns"].values)
            
            # Complexity penalty
            complexity = len(str(individual))
            penalty = settings.COMPLEXITY_PENALTY * complexity
            
            fitness = icir - penalty
            
            return (fitness,)
        except Exception as e:
            logger.debug(f"Evaluation error: {e}")
            return (0.0,)
    
    @staticmethod
    def _calculate_icir(alpha: np.ndarray, returns: np.ndarray) -> float:
        """Calculate Information Coefficient IR"""
        if len(alpha) < 2 or alpha.std() == 0:
            return 0.0
        
        # Correlation between alpha and forward returns
        alpha_norm = (alpha - alpha.mean()) / (alpha.std() + 1e-8)
        returns_norm = (returns - returns.mean()) / (returns.std() + 1e-8)
        
        correlation = np.mean(alpha_norm * returns_norm)
        
        return float(correlation * np.sqrt(252))
    
    async def evolve(self, training_data: pd.DataFrame, generations: int = 50) -> Optional[str]:
        """Evolve alpha expressions"""
        logger.info(f"Starting GP evolution for {self.strategy}...")
        
        pop = self.toolbox.population(n=100)
        hof = tools.HallOfFame(1)
        
        stats = tools.Statistics(lambda ind: ind.fitness.values)
        stats.register("avg", np.mean)
        stats.register("max", np.max)
        
        pop, logbook = tools.eaSimple(
            pop, self.toolbox,
            cxpb=0.7, mutpb=0.3,
            ngen=generations,
            stats=stats,
            halloffame=hof,
            verbose=False
        )
        
        if hof:
            best_expr = str(hof[0])
            best_fitness = hof[0].fitness.values[0]
            
            logger.info(f"Best expression: {best_expr}")
            logger.info(f"Fitness: {best_fitness:.4f}")
            
            # Validate OOS
            oos_valid = await self._validate_oos(best_expr, training_data)
            
            if oos_valid:
                self.best_expr = best_expr
                return best_expr
        
        return None
    
    async def _validate_oos(self, expr_str: str, data: pd.DataFrame) -> bool:
        """Validate expression on OOS data"""
        # Split into IS and OOS (last 7 days)
        split_idx = len(data) - int(len(data) * 0.1)
        oos_data = data.iloc[split_idx:]
        
        try:
            func = self.toolbox.compile(gp.PrimitiveTree.from_string(expr_str, self.pset))
            alpha = func(
                oos_data["close"].values,
                oos_data["volume"].values,
                oos_data["volatility"].values,
                oos_data["momentum"].values
            )
            
            icir = self._calculate_icir(alpha, oos_data["returns"].values)
            
            # Check minimum trade count
            signal_count = np.sum(np.abs(alpha) > alpha.std())
            
            is_valid = icir >= settings.ROLLING_ICIR_THRESHOLD and signal_count >= settings.MIN_TRADES_OOS
            
            logger.info(f"OOS validation: ICIR={icir:.4f}, trades={signal_count}, valid={is_valid}")
            
            return is_valid
        except Exception as e:
            logger.error(f"OOS validation error: {e}")
            return False
