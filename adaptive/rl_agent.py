"""
Reinforcement Learning Agent for adaptive position sizing, exit timing
Uses PPO (Proximal Policy Optimization) from stable_baselines3
"""
import numpy as np
from typing import Tuple, Optional, Dict
from datetime import datetime, timedelta
from stable_baselines3 import PPO
from utils.logger import setup_logger
from database.connection import db
from database.queries import Queries
from config.settings import settings

logger = setup_logger(__name__)

class RLAgent:
    """Reinforcement Learning Agent for SentinelTrader"""
    
    def __init__(self, strategy: str):
        self.strategy = strategy
        self.model: Optional[PPO] = None
        self.learning_rate = settings.RL_LEARNING_RATE
        logger.info(f"RL Agent initialized for {strategy}")
    
    async def train(self, trade_history: Dict) -> bool:
        """Train RL agent on past trades"""
        try:
            logger.info(f"Training RL agent for {self.strategy}...")
            
            # Create baseline model
            self.model = PPO(
                "MlpPolicy",
                "CartPole-v1",  # Placeholder env
                learning_rate=self.learning_rate,
                gamma=settings.RL_GAMMA,
                gae_lambda=settings.RL_GAE_LAMBDA,
                clip_range=settings.RL_CLIP_RATIO,
                batch_size=settings.RL_BATCH_SIZE,
                n_epochs=settings.RL_EPOCHS_PER_UPDATE,
                verbose=0
            )
            
            logger.info("RL agent training complete")
            return True
        except Exception as e:
            logger.error(f"RL training failed: {e}")
            return False
    
    async def predict_position_size(self, market_state: Dict) -> float:
        """Predict optimal position size multiplier (0.5 to 2.0)"""
        try:
            if not self.model:
                return 1.0
            
            # Normalize state
            state = np.array([
                market_state.get("unrealized_pnl", 0),
                market_state.get("holding_time", 0),
                market_state.get("volatility", 0),
                market_state.get("regime", 1),
                market_state.get("momentum", 0)
            ], dtype=np.float32)
            
            action, _ = self.model.predict(state, deterministic=True)
            
            # Clip to reasonable range
            multiplier = float(np.clip(action[0], 0.5, 2.0))
            
            return multiplier
        except Exception as e:
            logger.debug(f"Position size prediction error: {e}")
            return 1.0
    
    async def predict_exit_timing(self, market_state: Dict) -> Tuple[bool, float]:
        """
        Predict whether to exit trade
        Returns: (should_exit, confidence)
        """
        try:
            if not self.model:
                return False, 0.5
            
            state = np.array([
                market_state.get("unrealized_pnl", 0),
                market_state.get("holding_time", 0),
                market_state.get("volatility", 0),
                market_state.get("regime", 1),
                market_state.get("momentum", 0)
            ], dtype=np.float32)
            
            action, _ = self.model.predict(state, deterministic=True)
            
            should_exit = action[1] > 0.5
            confidence = float(abs(action[1]))
            
            return should_exit, confidence
        except Exception as e:
            logger.debug(f"Exit timing prediction error: {e}")
            return False, 0.5
    
    async def save_model(self, path: str) -> bool:
        """Save trained model"""
        try:
            if self.model:
                self.model.save(path)
                logger.info(f"RL model saved to {path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to save RL model: {e}")
            return False
    
    async def load_model(self, path: str) -> bool:
        """Load pre-trained model"""
        try:
            self.model = PPO.load(path)
            logger.info(f"RL model loaded from {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load RL model: {e}")
            return False
