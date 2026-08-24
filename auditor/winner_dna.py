"""
Analyze winning trades to extract patterns (DNA) for SentinelTrader
"""
import pandas as pd
import numpy as np
from typing import Dict, List
from utils.logger import setup_logger

logger = setup_logger(__name__)

class WinnerDNA:
    """Extract patterns from winning trades"""
    
    @staticmethod
    def analyze_winners(trades: List[Dict]) -> Dict:
        """Analyze winning trades"""
        
        winning_trades = [t for t in trades if t.get("pnl", 0) > 0]
        
        if not winning_trades:
            logger.warning("No winning trades found for DNA analysis")
            return {}
        
        pnl_pcts = [t.get("pnl_pct", 0) for t in winning_trades]
        holding_times = [t.get("holding_time", 0) for t in winning_trades]
        risk_rewards = [t.get("risk_reward_ratio", 0) for t in winning_trades]
        
        avg_pnl = np.mean(pnl_pcts) if pnl_pcts else 0
        avg_holding = np.mean(holding_times) if holding_times else 0
        avg_risk_reward = np.mean(risk_rewards) if risk_rewards else 0
        
        dna = {
            "avg_pnl_pct": avg_pnl,
            "avg_holding_time_hours": avg_holding,
            "avg_risk_reward_ratio": avg_risk_reward,
            "win_count": len(winning_trades),
            "win_rate": len(winning_trades) / len(trades) if trades else 0,
            "total_profit": sum(t.get("pnl", 0) for t in winning_trades)
        }
        
        logger.info(f"Winner DNA: {dna}")
        
        return dna
    
    @staticmethod
    def analyze_losers(trades: List[Dict]) -> Dict:
        """Analyze losing trades to learn from mistakes"""
        
        losing_trades = [t for t in trades if t.get("pnl", 0) < 0]
        
        if not losing_trades:
            return {}
        
        pnl_pcts = [t.get("pnl_pct", 0) for t in losing_trades]
        holding_times = [t.get("holding_time", 0) for t in losing_trades]
        
        avg_loss = np.mean(pnl_pcts) if pnl_pcts else 0
        avg_holding = np.mean(holding_times) if holding_times else 0
        
        dna = {
            "avg_loss_pct": avg_loss,
            "avg_holding_time_hours": avg_holding,
            "loss_count": len(losing_trades),
            "total_loss": sum(t.get("pnl", 0) for t in losing_trades)
        }
        
        logger.info(f"Loser DNA: {dna}")
        
        return dna
