"""
Z-Score calculation for signal generation
"""
import numpy as np
import pandas as pd
from typing import List, Optional
from utils.logger import setup_logger

logger = setup_logger(__name__)

class ZScoreCalculator:
    """Calculate Z-Score for entries/exits"""
    
    @staticmethod
    def calculate(data: pd.DataFrame, period: int = 20) -> pd.Series:
        """Calculate Z-Score"""
        try:
            close = data["close"]
            ma = close.rolling(window=period).mean()
            std = close.rolling(window=period).std()
            
            z_score = (close - ma) / (std + 1e-8)
            return z_score
        except Exception as e:
            logger.error(f"Z-Score calculation error: {e}")
            return pd.Series(0, index=data.index)
    
    @staticmethod
    def mean_reversion_signal(z_score: pd.Series, entry_threshold: float = 2.0, exit_threshold: float = 0.5) -> pd.Series:
        """
        Mean reversion signals
        Long: Z-Score < -entry_threshold
        Exit: Z-Score > -exit_threshold
        """
        signal = pd.Series(0, index=z_score.index)
        
        signal[z_score < -entry_threshold] = 1  # Long entry
        signal[(z_score > -exit_threshold) & (signal.shift() == 1)] = 0  # Exit
        
        return signal.ffill()
    
    @staticmethod
    def momentum_signal(z_score: pd.Series, entry_threshold: float = 2.0) -> pd.Series:
        """
        Momentum signals
        Long: Z-Score > entry_threshold
        Exit: Z-Score < exit_threshold
        """
        signal = pd.Series(0, index=z_score.index)
        
        signal[z_score > entry_threshold] = 1
        signal[z_score < -1] = 0
        
        return signal.ffill()
