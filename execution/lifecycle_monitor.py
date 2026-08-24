"""
Monitor and manage trade lifecycle for SentinelTrader
"""
import asyncio
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from utils.logger import setup_logger
from database.queries import Queries
from config.settings import settings

logger = setup_logger(__name__)

class LifecycleMonitor:
    """Monitor active trades and manage their lifecycle"""
    
    def __init__(self):
        self.running = True
    
    async def run(self):
        """Main lifecycle loop"""
        while self.running:
            try:
                await self._check_open_trades()
                await asyncio.sleep(settings.LIFECYCLE_CHECK_INTERVAL)
            except Exception as e:
                logger.error(f"Lifecycle monitor error: {e}")
                await asyncio.sleep(10)
    
    async def _check_open_trades(self):
        """Check and update open trades"""
        try:
            # Fetch open positions
            arb_positions = await Queries.get_open_positions("arbitrage")
            meme_positions = await Queries.get_open_positions("meme")
            
            all_positions = arb_positions + meme_positions
            
            for pos in all_positions:
                try:
                    asset = pos.get("asset")
                    entry_price = pos.get("entry_price", 0)
                    current_price = pos.get("current_price", entry_price)
                    unrealized_pnl_pct = (current_price - entry_price) / entry_price if entry_price > 0 else 0
                    
                    # Example: Exit if 5% profit
                    if unrealized_pnl_pct > 0.05:
                        logger.info(f"Closing {asset} on profit target (+{unrealized_pnl_pct*100:.2f}%)")
                        # Close position logic here
                    
                    # Example: Exit if 3% loss
                    elif unrealized_pnl_pct < -0.03:
                        logger.info(f"Closing {asset} on stop loss ({unrealized_pnl_pct*100:.2f}%)")
                        # Close position logic here
                    
                    # Check max holding time
                    entry_time = pos.get("entry_time")
                    if entry_time:
                        holding_time = (datetime.utcnow() - entry_time).total_seconds() / 3600
                        if holding_time > 24:  # 24 hours
                            logger.info(f"Closing {asset} on max holding time")
                            # Close position logic here
                
                except Exception as e:
                    logger.error(f"Error processing position {pos.get('asset')}: {e}")
        
        except Exception as e:
            logger.error(f"Trade check error: {e}")
    
    def stop(self):
        """Stop lifecycle monitor"""
        self.running = False
        logger.info("Lifecycle monitor stopped")
