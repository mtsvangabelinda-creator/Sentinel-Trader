"""
Composite signal scoring for SentinelTrader
"""
import numpy as np
import pandas as pd
from typing import Dict, List
from utils.logger import setup_logger

logger = setup_logger(__name__)

class SignalScorer:
    """Score and rank signals"""
    
    @staticmethod
    def composite_score(
        alpha_signal: float,
        z_score: float,
        game_theory_score: float,
        regime_weight: float = 1.0,
        volume_score: float = 0.5
    ) -> float:
        """
        Calculate composite signal score
        Weighted combination of all signal components
        """
        # Normalize components to [-1, 1]
        alpha_norm = np.tanh(alpha_signal) if isinstance(alpha_signal, (int, float)) else 0
        z_norm = np.tanh(z_score / 3) if z_score != 0 else 0
        
        # Weights
        score = (
            0.3 * alpha_norm +
            0.3 * z_norm +
            0.25 * game_theory_score +
            0.15 * volume_score
        ) * regime_weight
        
        return float(score)
    
    @staticmethod
    def rank_signals(signals: list) -> list:
        """Rank signals by score"""
        sorted_signals = sorted(signals, key=lambda x: x.get("score", 0), reverse=True)
        return sorted_signals
