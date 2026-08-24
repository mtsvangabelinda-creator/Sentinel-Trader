"""
Extract trading features for analysis in SentinelTrader
"""
import pandas as pd
import numpy as np
from typing import Dict
from utils.logger import setup_logger

logger = setup_logger(__name__)

class FeatureExtractor:
    """Extract features from trades"""
    
    @staticmethod
    def extract_trade_features(trade: Dict) -> Dict:
        """Extract features from single trade"""
        
        entry = trade.get("entry_price", 0)
        exit_price = trade.get("exit_price", 0)
        
        if entry == 0:
            return {}
        
        pnl_pct = (exit_price - entry) / entry if exit_price > 0 else 0
        
        entry_time = trade.get("entry_time")
        exit_time = trade.get("exit_time")
        holding_time = 0
        if entry_time and exit_time:
            holding_time = (exit_time - entry_time).total_seconds() / 3600
        
        tp = trade.get("take_profit", entry * 1.05)
        sl = trade.get("stop_loss", entry * 0.95)
        
        risk_reward_ratio = abs((tp - entry) / (entry - sl + 1e-8)) if sl != entry else 0
        
        features = {
            "pnl_pct": pnl_pct,
            "holding_time": holding_time,
            "risk_reward_ratio": risk_reward_ratio,
            "entry_price": entry,
            "exit_price": exit_price,
        }
        
        return features
