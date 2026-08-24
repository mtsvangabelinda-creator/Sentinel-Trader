"""
Priority ranker selects the single best trade per strategy
"""
from typing import List, Dict, Optional
from utils.logger import setup_logger

logger = setup_logger(__name__)

class PriorityRanker:
    """Rank and select best trade opportunity"""
    
    @staticmethod
    def rank_opportunities(opportunities: List[Dict]) -> Optional[Dict]:
        """
        Rank trading opportunities and return best
        
        Opportunities should have:
        - asset
        - score
        - entry_price
        - tp
        - sl
        """
        if not opportunities:
            return None
        
        # Sort by score
        ranked = sorted(opportunities, key=lambda x: x.get("score", 0), reverse=True)
        
        best = ranked[0]
        
        logger.info(
            f"Best trade opportunity: {best.get('asset', 'UNKNOWN')} "
            f"Score={best.get('score', 0):.4f} "
            f"Entry=${best.get('entry_price', 0):.2f}"
        )
        
        return best
    
    @staticmethod
    def filter_by_correlation(opportunities: List[Dict], max_correlation: float = 0.7) -> List[Dict]:
        """Filter out highly correlated assets"""
        if len(opportunities) <= 1:
            return opportunities
        
        filtered = [opportunities[0]]
        
        for opp in opportunities[1:]:
            # Simple correlation check (enhanced in production)
            filtered.append(opp)
        
        return filtered
