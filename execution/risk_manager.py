"""
Risk management and circuit breakers for SentinelTrader
"""
from typing import Dict, List
from utils.logger import setup_logger
from database.queries import Queries
from config.settings import settings

logger = setup_logger(__name__)

class RiskManager:
    """Manage portfolio risk and enforce circuit breakers"""
    
    def __init__(self):
        self.daily_loss_pct = 0.0
        self.max_drawdown_reached = False
        self.strategy_frozen: Dict[str, bool] = {
            "arbitrage": False,
            "meme": False
        }
        self.frozen_until: Dict[str, float] = {
            "arbitrage": 0.0,
            "meme": 0.0
        }
    
    async def check_daily_loss_limit(self, strategy: str, daily_return: float) -> bool:
        """Check daily loss limit circuit breaker"""
        if daily_return <= -settings.DAILY_LOSS_LIMIT_PCT:
            logger.warning(f"{strategy} hit daily loss limit: {daily_return*100:.2f}%")
            self.strategy_frozen[strategy] = True
            
            await Queries.save_risk_event(
                strategy,
                "DAILY_LOSS_LIMIT",
                "high",
                f"Daily loss: {daily_return*100:.2f}%",
                f"Strategy frozen for 24h"
            )
            
            return False
        
        return True
    
    async def check_max_drawdown(self, equity_curve: list) -> bool:
        """Check maximum drawdown circuit breaker"""
        if not equity_curve or len(equity_curve) < 2:
            return True
        
        import numpy as np
        equity = np.array(equity_curve)
        peak = np.maximum.accumulate(equity)
        drawdown = (equity - peak) / (peak + 1e-8)
        max_dd = np.min(drawdown)
        
        if max_dd <= -settings.MAX_DRAWDOWN_PCT:
            logger.warning(f"Max drawdown limit reached: {max_dd*100:.2f}%")
            self.max_drawdown_reached = True
            
            await Queries.save_risk_event(
                "system",
                "MAX_DRAWDOWN_LIMIT",
                "critical",
                f"Max drawdown: {max_dd*100:.2f}%",
                "All strategies halted"
            )
            
            return False
        
        return True
    
    async def check_icir_breaker(self, strategy: str, icir: float, failure_count: int = 0) -> bool:
        """Check ICIR performance breaker"""
        if icir < settings.ROLLING_ICIR_THRESHOLD:
            if failure_count >= settings.ICIR_FAIL_WINDOW:
                logger.warning(f"{strategy} ICIR breaker triggered: {icir:.4f}")
                self.strategy_frozen[strategy] = True
                
                await Queries.save_risk_event(
                    strategy,
                    "ICIR_BREAKER",
                    "high",
                    f"ICIR: {icir:.4f} (threshold: {settings.ROLLING_ICIR_THRESHOLD})",
                    "Strategy frozen"
                )
                
                return False
        
        return True
    
    def is_strategy_frozen(self, strategy: str) -> bool:
        """Check if strategy is frozen"""
        return self.strategy_frozen.get(strategy, False)
    
    def unfreeze_strategy(self, strategy: str):
        """Unfreeze strategy"""
        self.strategy_frozen[strategy] = False
        logger.info(f"{strategy} unfrozen")
