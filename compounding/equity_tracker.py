"""
Track equity curve and compounding growth for SentinelTrader
"""
from typing import List, Dict
from datetime import datetime, date
import numpy as np
from utils.logger import setup_logger
from database.queries import Queries
from utils.helpers import calculate_annualized_sharpe, calculate_max_drawdown, calculate_icir

logger = setup_logger(__name__)

class EquityTracker:
    """Track account equity and performance"""
    
    def __init__(self, initial_capital: float):
        self.initial_capital = initial_capital
        self.current_equity = initial_capital
        self.equity_curve: List[float] = [initial_capital]
        self.daily_returns: List[float] = []
    
    async def update_equity(self, new_equity: float):
        """Update current equity"""
        self.equity_curve.append(new_equity)
        
        if len(self.equity_curve) > 1:
            prev_equity = self.equity_curve[-2]
            if prev_equity > 0:
                daily_return = (new_equity - prev_equity) / prev_equity
                self.daily_returns.append(daily_return)
                self.current_equity = new_equity
    
    async def get_performance_metrics(self) -> Dict:
        """Calculate performance metrics"""
        
        if len(self.equity_curve) < 2:
            return {}
        
        total_return = (self.equity_curve[-1] - self.initial_capital) / self.initial_capital
        
        metrics = {
            "total_return": total_return,
            "current_equity": self.equity_curve[-1],
            "daily_returns": self.daily_returns,
            "sharpe_ratio": calculate_annualized_sharpe(self.daily_returns),
            "max_drawdown": calculate_max_drawdown(self.equity_curve),
            "icir": calculate_icir(self.daily_returns),
            "num_days": len(self.equity_curve)
        }
        
        return metrics
    
    async def get_equity_curve(self) -> List[float]:
        """Get full equity curve"""
        return self.equity_curve
