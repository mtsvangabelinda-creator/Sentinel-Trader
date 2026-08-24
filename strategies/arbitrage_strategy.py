"""
Arbitrage Strategy: Large-cap assets with focus on cross-exchange spreads
"""
import asyncio
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from utils.logger import setup_logger
from database.queries import Queries
from signal_engine.aggregator import SignalAggregator
from priority_ranker.ranker import PriorityRanker
from config.settings import settings

logger = setup_logger(__name__)

class ArbitrageStrategy:
    """Large-cap arbitrage strategy for SentinelTrader (BTC, ETH, SOL, etc.)"""
    
    def __init__(self):
        self.name = "arbitrage"
        self.assets = settings.ARBITRAGE_ASSETS
        self.signal_aggregator = SignalAggregator(self.name)
        self.active_positions: Dict[str, Dict] = {}
        logger.info(f"Arbitrage strategy initialized with assets: {self.assets}")
    
    async def generate_signals(self, market_data: Dict, regime: int, evolved_alpha: Optional[float]) -> Optional[Dict]:
        """Generate trading signal"""
        
        try:
            signals = await self.signal_aggregator.aggregate(market_data, regime, evolved_alpha)
            
            # Composite score
            composite_score = sum(s["value"] * s["weight"] for s in signals) / sum(s["weight"] for s in signals) if signals else 0
            
            # Arbitrage threshold: conservative
            if composite_score > 0.3:
                opportunity = {
                    "strategy": self.name,
                    "asset": market_data.get("asset", "BTC"),
                    "score": composite_score,
                    "entry_price": market_data.get("close", 0),
                    "tp": market_data.get("close", 0) * 1.03,  # 3% target
                    "sl": market_data.get("close", 0) * 0.98,  # 2% stop
                    "timestamp": datetime.utcnow()
                }
                
                logger.info(f"Arbitrage signal: {opportunity['asset']} Score={composite_score:.4f}")
                return opportunity
        
        except Exception as e:
            logger.error(f"Signal generation error in arbitrage: {e}")
        
        return None
    
    async def execute(self, opportunity: Dict) -> bool:
        """Execute trade"""
        logger.info(f"Executing arbitrage trade: {opportunity['asset']}")
        try:
            # Save to database
            await Queries.save_trade({
                "strategy": self.name,
                "asset": opportunity["asset"],
                "entry_price": opportunity["entry_price"],
                "quantity": 0.0,  # Will be calculated by position sizer
                "entry_time": opportunity["timestamp"]
            })
            return True
        except Exception as e:
            logger.error(f"Arbitrage execution error: {e}")
            return False
