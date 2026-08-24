import aiohttp
from typing import Dict, List, Optional
from utils.logger import setup_logger
from utils.helpers import exponential_backoff

logger = setup_logger(__name__)

class BinanceFetcher:
    """Fetch external price data from Binance for gap detection"""
    
    BASE_URL = "https://api.binance.com/api/v3"
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    @exponential_backoff(max_retries=3)
    async def get_klines(self, symbol: str, interval: str = "15m", limit: int = 500) -> Optional[List]:
        """Fetch klines (OHLCV)"""
        if not self.session:
            raise RuntimeError("Session not initialized")
        
        url = f"{self.BASE_URL}/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        
        try:
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.json()
                return None
        except Exception as e:
            logger.error(f"Binance klines error: {e}")
            raise
    
    @exponential_backoff(max_retries=3)
    async def get_price(self, symbol: str) -> Optional[float]:
        """Get current price"""
        if not self.session:
            raise RuntimeError("Session not initialized")
        
        url = f"{self.BASE_URL}/ticker/price"
        params = {"symbol": symbol}
        
        try:
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return float(data.get("price", 0))
                return None
        except Exception as e:
            logger.error(f"Binance price error: {e}")
            raise
