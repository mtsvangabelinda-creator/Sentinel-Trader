"""
Order execution via Kraken API for SentinelTrader
"""
import asyncio
import ccxt.async_support as ccxt
from typing import Dict, Optional
from datetime import datetime
from utils.logger import setup_logger
from database.queries import Queries
from config.settings import settings

logger = setup_logger(__name__)

class OrderManager:
    """Manage order lifecycle on Kraken"""
    
    def __init__(self):
        self.exchange: Optional[ccxt.kraken] = None
    
    async def connect(self):
        """Connect to Kraken"""
        try:
            self.exchange = ccxt.kraken({
                "apiKey": settings.KRAKEN_API_KEY,
                "secret": settings.KRAKEN_API_SECRET,
                "enableRateLimit": True
            })
            await self.exchange.load_markets()
            logger.info("Connected to Kraken")
        except Exception as e:
            logger.error(f"Kraken connection failed: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from Kraken"""
        if self.exchange:
            await self.exchange.close()
            logger.info("Disconnected from Kraken")
    
    async def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float
    ) -> Optional[Dict]:
        """Place market order on Kraken"""
        try:
            if not self.exchange:
                logger.error("Exchange not connected")
                return None
            
            order = await self.exchange.create_market_order(
                symbol,
                side,
                quantity
            )
            
            logger.info(f"Order placed: {order.get('id')} {side} {quantity} {symbol}")
            
            # Save to database
            asset = symbol.split("/")[0]
            await Queries.save_trade({
                "strategy": "unknown",
                "asset": asset,
                "entry_price": order.get("average", 0),
                "quantity": quantity,
                "entry_time": datetime.utcnow(),
                "order_id": order.get("id")
            })
            
            return order
        except Exception as e:
            logger.error(f"Order placement failed: {e}")
            return None
    
    async def place_stop_loss_order(
        self,
        symbol: str,
        quantity: float,
        stop_price: float
    ) -> Optional[Dict]:
        """Place stop loss order"""
        try:
            if not self.exchange:
                logger.error("Exchange not connected")
                return None
            
            order = await self.exchange.create_order(
                symbol,
                "market",
                "sell",
                quantity,
                params={
                    "stopPrice": stop_price
                }
            )
            
            logger.info(f"Stop loss order placed: {order.get('id')}")
            return order
        except Exception as e:
            logger.error(f"Stop loss order failed: {e}")
            return None
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel open order"""
        try:
            if not self.exchange:
                logger.error("Exchange not connected")
                return False
            
            await self.exchange.cancel_order(order_id, symbol)
            logger.info(f"Order cancelled: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Order cancellation failed: {e}")
            return False
    
    async def get_order_status(self, order_id: str, symbol: str) -> Optional[Dict]:
        """Get order status"""
        try:
            if not self.exchange:
                return None
            
            order = await self.exchange.fetch_order(order_id, symbol)
            return order
        except Exception as e:
            logger.error(f"Order status fetch failed: {e}")
            return None
