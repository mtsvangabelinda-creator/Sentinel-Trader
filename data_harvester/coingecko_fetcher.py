import aiohttp
from typing import Dict, Optional, List
from utils.logger import setup_logger
from utils.helpers import exponential_backoff

logger = setup_logger(__name__)

class CoinGeckoFetcher:
    """Fetch market data from CoinGecko (free)"""
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    @exponential_backoff(max_retries=3)
    async def get_market_data(self, coin_id: str) -> Optional[Dict]:
        """Get market data (market cap, volume, etc.)"""
        if not self.session:
            raise RuntimeError("Session not initialized")
        
        url = f"{self.BASE_URL}/coins/{coin_id}"
        params = {
            "localization": False,
            "tickers": False,
            "market_data": True
        }
        
        try:
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.json()
                return None
        except Exception as e:
            logger.error(f"CoinGecko market data error: {e}")
            raise
    
    @exponential_backoff(max_retries=3)
    async def search(self, query: str) -> Optional[List]:
        """Search coins"""
        if not self.session:
            raise RuntimeError("Session not initialized")
        
        url = f"{self.BASE_URL}/search"
        params = {"query": query}
        
        try:
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("coins", [])
                return None
        except Exception as e:
            logger.error(f"CoinGecko search error: {e}")
            raise
