"""
Meme Strategy: Small-cap, volatile tokens with high volume
Focus on trends and sentiment
"""
import asyncio
from typing import Dict, Optional
from datetime import datetime, time
from utils.logger import setup_logger
from database.queries import Queries
from signal_engine.aggregator import SignalAggregator
from config.settings import settings

logger = setup_logger(__name__)

class MemeStrategy:
    """Small-cap meme token strategy for SentinelTrader"""
    
    def __init__(self):
        self.name = "meme"
        self.assets = settings.MEME_ASSETS
        self.signal_aggregator = SignalAggregator(self.name)
        self.active_positions: Dict[str, Dict] = {}
        self.force_close_hour = settings.FORCE_CLOSE_HOUR_MEME
        logger.info(f"Meme strategy initialized with assets: {self.assets}")
    
    async def generate_signals(self, market_data: Dict, regime: int, evolved_alpha: Optional[float]) -> Optional[Dict]:
        """Generate meme trade signal"""
        
        try:
            signals = await self.signal_aggregator.aggregate(market_data, regime, evolved_alpha)
            
            composite_score = sum(s["value"] * s["weight"] for s in signals) / sum(s["weight"] for s in signals) if signals else 0
            
            # Meme threshold: higher risk tolerance
            if composite_score > 0.5:
                opportunity = {
                    "strategy": self.name,
                    "asset": market_data.get("asset", "WIF"),
                    "score": composite_score,
                    "entry_price": market_data.get("close", 0),
                    "tp": market_data.get("close", 0) * 1.10,  # 10% target
                    "sl": market_data.get("close", 0) * 0.90,  # 10% stop
                    "timestamp": datetime.utcnow()
                }
                
                logger.info(f"Meme signal: {opportunity['asset']} Score={composite_score:.4f}")
                return opportunity
        
        except Exception as e:
            logger.error(f"Signal generation error in meme: {e}")
        
        return None
    
    async def check_force_close(self) -> bool:
        """Check if force close hour reached"""
        current_hour = datetime.utcnow().hour
        return current_hour >= self.force_close_hour
    
    async def force_close_positions(self):
        """Force close all open positions at daily cutoff"""
        logger.warning(f"Force closing all meme positions at {self.force_close_hour}:00 UTC")
        
        try:
            positions = await Queries.get_open_positions(self.name)
            
            for pos in positions:
                # Close position at market
                logger.info(f"Force closing {pos.get('asset')}")
                
                await Queries.close_trade(
                    pos.get("id"),
                    pos.get("current_price", pos.get("entry_price")),
                    datetime.utcnow(),
                    0.0
                )
        except Exception as e:
            logger.error(f"Force close error: {e}")
    
    async def execute(self, opportunity: Dict) -> bool:
        """Execute trade"""
        logger.info(f"Executing meme trade: {opportunity['asset']}")
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
            logger.error(f"Meme execution error: {e}")
            return False
