"""
Oversight loop monitors module performance and disables underperformers
"""
import asyncio
from typing import Dict, List
from datetime import datetime, timedelta
from utils.logger import setup_logger
from database.connection import db
from database.queries import Queries
from config.settings import settings

logger = setup_logger(__name__)

class OversightLoop:
    """Monitor and optimize system performance"""
    
    def __init__(self):
        self.module_scores: Dict[str, float] = {}
        self.disabled_modules: set = set()
    
    async def run(self):
        """Main oversight loop"""
        while True:
            try:
                await self._check_performance()
                await self._adjust_weights()
                await asyncio.sleep(settings.OVERSIGHT_CHECK_INTERVAL)
            except Exception as e:
                logger.error(f"Oversight loop error: {e}")
                await asyncio.sleep(60)
    
    async def _check_performance(self):
        """Check performance of each module"""
        strategies = ["arbitrage", "meme"]
        
        for strategy in strategies:
            try:
                perf = await Queries.get_performance_summary(strategy, days=7)
                
                if perf and perf.get("avg_sharpe") is not None:
                    sharpe = perf.get("avg_sharpe", 0) or 0
                    win_rate = perf.get("avg_win_rate", 0) or 0
                    
                    # Calculate composite score
                    score = (sharpe * 0.6) + (win_rate * 0.4)
                    self.module_scores[strategy] = score
                    
                    # Disable underperformers
                    if score < settings.UNDERPERFORMER_THRESHOLD:
                        self.disabled_modules.add(strategy)
                        logger.warning(f"Disabled {strategy} due to low score: {score:.4f}")
                        
                        # Log risk event
                        await Queries.save_risk_event(
                            strategy,
                            "UNDERPERFORMER_DISABLED",
                            "high",
                            f"Score: {score:.4f}",
                            "Temporarily disabled"
                        )
                    else:
                        # Re-enable if score improves
                        if strategy in self.disabled_modules:
                            self.disabled_modules.remove(strategy)
                            logger.info(f"Re-enabled {strategy}")
            except Exception as e:
                logger.error(f"Performance check error for {strategy}: {e}")
    
    async def _adjust_weights(self):
        """Adjust strategy weights based on performance"""
        if not self.module_scores:
            return
        
        total_score = sum(self.module_scores.values())
        if total_score == 0:
            return
        
        weights = {k: v / total_score for k, v in self.module_scores.items()}
        
        logger.debug(f"Updated module weights: {weights}")
    
    def is_enabled(self, strategy: str) -> bool:
        """Check if strategy is enabled"""
        return strategy not in self.disabled_modules
