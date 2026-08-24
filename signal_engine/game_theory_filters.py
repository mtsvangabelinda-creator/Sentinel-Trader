"""
Game theory based filters to improve signal quality
- Kelly Criterion position sizing
- Risk/Reward analysis
"""
import numpy as np
from typing import Tuple, Dict
from utils.logger import setup_logger

logger = setup_logger(__name__)

class GameTheoryFilters:
    """Game theory based trade filtering"""
    
    @staticmethod
    def kelly_criterion(win_rate: float, avg_win: float, avg_loss: float) -> float:
        """
        Calculate Kelly Criterion fraction
        f = (bp - q) / b
        where: b = odds, p = win prob, q = 1-p
        """
        if avg_loss == 0 or avg_win == 0:
            return 0.25
        
        b = avg_win / avg_loss
        p = win_rate
        q = 1 - win_rate
        
        f = (b * p - q) / b
        
        # Fractional Kelly (conservative)
        f_frac = f * 0.25
        
        return float(np.clip(f_frac, 0.01, 0.50))
    
    @staticmethod
    def competitive_payoff_score(entry_price: float, tp: float, sl: float, win_prob: float) -> float:
        """
        Score trade setup based on risk/reward
        High score = good setup
        """
        if entry_price == 0 or tp == entry_price:
            return 0.0
        
        reward = abs(tp - entry_price) / entry_price
        risk = abs(entry_price - sl) / entry_price
        
        if risk == 0:
            return 0.0
        
        ratio = reward / risk
        
        # Bayesian payoff expectancy
        payoff = (win_prob * reward) - ((1 - win_prob) * risk)
        
        return float(payoff * ratio)
    
    @staticmethod
    def cooperative_clustering_score(similar_signals: int, total_signals: int) -> float:
        """
        Score based on signal agreement
        High score = multiple signals align
        """
        if total_signals == 0:
            return 0.0
        
        agreement = similar_signals / total_signals
        
        return float(agreement)
