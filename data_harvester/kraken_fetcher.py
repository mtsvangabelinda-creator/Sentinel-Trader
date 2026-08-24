import aiohttp
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from utils.logger import setup_logger
from utils.helpers import exponential_backoff
from config.settings import settings

logger = setup_logger(__name__)

class KrakenFetcher:
    """Fetch OHLCV and order book data from Kraken"""
    
    BASE_URL = "https://api.kraken.com/0"
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    @exponential_backoff(max_retries=3)
    async def get_ohlcv(self, pair: str, interval: int = 15) -> Optional[List]:
        """
        Fetch OHLCV data
        interval: 1, 5, 15, 30, 60, 240, 1440, 10080, 21600
        """
        if not self.session:
            raise RuntimeError("Session not initialized")
        
        url = f"{self.BASE_URL}/public/OHLC"
        params = {
            "pair": pair,
            "interval": interval
        }
        
        try:
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("result"):
                        return data["result"].get(pair, [])
                else:
                    logger.error(f"Kraken OHLCV error {resp.status} for {pair}")
                    return None
        except Exception as e:
            logger.error(f"Kraken OHLCV fetch error: {e}")
            raise
    
    @exponential_backoff(max_retries=3)
    async def get_trades(self, pair: str, since: Optional[int] = None) -> Optional[List]:
        """Fetch recent trades"""
        if not self.session:
            raise RuntimeError("Session not initialized")
        
        url = f"{self.BASE_URL}/public/Trades"
        params = {"pair": pair}
        if since:
            params["since"] = since
        
        try:
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("result"):
                        return data["result"].get(pair, [])
                return None
        except Exception as e:
            logger.error(f"Kraken trades fetch error: {e}")
            raise
    
    @exponential_backoff(max_retries=3)
    async def get_order_book(self, pair: str, count: int = 50) -> Optional[Dict]:
        """Fetch order book"""
        if not self.session:
            raise RuntimeError("Session not initialized")
        
        url = f"{self.BASE_URL}/public/Depth"
        params = {
            "pair": pair,
            "count": count
        }
        
        try:
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("result"):
                        return data["result"].get(pair)
                return None
        except Exception as e:
            logger.error(f"Kraken order book error: {e}")
            raise
    
    @exponential_backoff(max_retries=3)
    async def get_asset_pairs(self) -> Optional[Dict]:
        """Get tradable asset pairs"""
        if not self.session:
            raise RuntimeError("Session not initialized")
        
        url = f"{self.BASE_URL}/public/AssetPairs"
        
        try:
            async with self.session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("result", {})
                return None
        except Exception as e:
            logger.error(f"Kraken asset pairs error: {e}")
            raise
    
    @exponential_backoff(max_retries=3)
    async def get_ticker(self, pair: str) -> Optional[Dict]:
        """Get current ticker info"""
        if not self.session:
            raise RuntimeError("Session not initialized")
        
        url = f"{self.BASE_URL}/public/Ticker"
        params = {"pair": pair}
        
        try:
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("result"):
                        return data["result"].get(pair)
                return None
        except Exception as e:
            logger.error(f"Kraken ticker error: {e}")
            raise
