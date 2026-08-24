"""
Evolve strategy parameters based on winner DNA for SentinelTrader
"""
from typing import Dict
from utils.logger import setup_logger

logger = setup_logger(__name__)

class EvolutionEngine:
    """Evolve strategy parameters toward winner patterns"""
    
    @staticmethod
    def evolve_parameters(current_params: Dict, winner_dna: Dict) -> Dict:
        """
        Evolve strategy parameters toward winner DNA patterns
        """
        evolved = current_params.copy()
        
        if not winner_dna:
            return evolved
        
        try:
            # Move parameters toward winner patterns
            if winner_dna.get("avg_holding_time_hours"):
                evolved["target_holding_time"] = winner_dna["avg_holding_time_hours"]
            
            if winner_dna.get("avg_risk_reward_ratio") and winner_dna["avg_risk_reward_ratio"] > 1:
                evolved["target_risk_reward"] = winner_dna["avg_risk_reward_ratio"]
            
            if winner_dna.get("avg_pnl_pct"):
                evolved["target_pnl_pct"] = winner_dna["avg_pnl_pct"]
            
            logger.info(f"Evolved parameters: {evolved}")
            
            return evolved
        except Exception as e:
            logger.error(f"Parameter evolution error: {e}")
            return current_params
    
    @staticmethod
    def calculate_adaptation_score(current_metrics: Dict, target_dna: Dict) -> float:
        """Calculate how well current strategy matches target DNA"""
        
        if not target_dna:
            return 0.5
        
        score = 0.0
        weight_sum = 0.0
        
        # PnL alignment
        if target_dna.get("avg_pnl_pct"):
            pnl_diff = abs(current_metrics.get("avg_pnl_pct", 0) - target_dna["avg_pnl_pct"])
            pnl_score = 1.0 - min(pnl_diff, 1.0)
            score += pnl_score * 0.4
            weight_sum += 0.4
        
        # Holding time alignment
        if target_dna.get("avg_holding_time_hours"):
            time_diff = abs(current_metrics.get("avg_holding_time", 0) - target_dna["avg_holding_time_hours"])
            time_score = 1.0 - min(time_diff / 24, 1.0)  # Normalize to 24 hours
            score += time_score * 0.3
            weight_sum += 0.3
        
        # Risk/Reward alignment
        if target_dna.get("avg_risk_reward_ratio"):
            rr_diff = abs(current_metrics.get("risk_reward_ratio", 1.0) - target_dna["avg_risk_reward_ratio"])
            rr_score = 1.0 - min(rr_diff, 1.0)
            score += rr_score * 0.3
            weight_sum += 0.3
        
        if weight_sum > 0:
            return score / weight_sum
        
        return 0.5
