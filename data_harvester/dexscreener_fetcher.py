import aiohttp
from typing import Dict, List, Optional
from utils.logger import setup_logger
from utils.helpers import exponential_backoff

logger = setup_logger(__name__)

class DexScreenerFetcher:
    """Fetch DEX pool data"""
    
    BASE_URL = "https://api.dexscreener.com/latest/dex"
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    @exponential_backoff(max_retries=3)
    async def search_tokens(self, query: str) -> Optional[Dict]:
        """Search tokens"""
        if not self.session:
            raise RuntimeError("Session not initialized")
        
        url = f"{self.BASE_URL}/search"
        params = {"q": query}
        
        try:
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("pairs", [])
                return None
        except Exception as e:
            logger.error(f"DexScreener search error: {e}")
            raise
    
    @exponential_backoff(max_retries=3)
    async def get_pool_by_address(self, chain_id: str, pool_address: str) -> Optional[Dict]:
        """Get pool data by address"""
        if not self.session:
            raise RuntimeError("Session not initialized")
        
        url = f"{self.BASE_URL}/pair/{chain_id}/{pool_address}"
        
        try:
            async with self.session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("pair")
                return None
        except Exception as e:
            logger.error(f"DexScreener pool error: {e}")
            raise
