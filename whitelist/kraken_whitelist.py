"""
Whitelist manager for Kraken tradable assets
"""
import asyncio
import redis.asyncio as redis
from typing import Set, Dict, Optional
from datetime import datetime, timedelta
from data_harvester.kraken_fetcher import KrakenFetcher
from database.connection import db
from database.queries import Queries
from utils.logger import setup_logger
from config.settings import settings

logger = setup_logger(__name__)

class KrakenWhitelist:
    """Manage Kraken tradable assets"""
    
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.whitelist: Set[str] = set()
    
    async def connect(self):
        """Connect to Redis cache"""
        try:
            self.redis = await redis.from_url(settings.REDIS_URL)
            logger.info("Connected to Redis for whitelist caching")
        except Exception as e:
            logger.warning(f"Redis connection failed (continuing without cache): {e}")
            self.redis = None
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
    
    async def is_tradable(self, asset: str) -> bool:
        """Check if asset is tradable on Kraken"""
        pair = f"{asset}USD"
        
        # Check cache first
        if self.redis:
            try:
                cached = await self.redis.get(f"tradable:{asset}")
                if cached is not None:
                    return cached == b"1"
            except Exception as e:
                logger.debug(f"Redis cache check failed: {e}")
        
        # Fetch from Kraken
        try:
            async with KrakenFetcher() as fetcher:
                pairs = await fetcher.get_asset_pairs()
                is_tradable = pair in pairs if pairs else False
                
                # Cache result
                if self.redis:
                    try:
                        await self.redis.setex(
                            f"tradable:{asset}",
                            settings.WHITELIST_CACHE_TTL,
                            "1" if is_tradable else "0"
                        )
                    except Exception as e:
                        logger.debug(f"Redis cache set failed: {e}")
                
                return is_tradable
        except Exception as e:
            logger.error(f"Whitelist check failed for {asset}: {e}")
            return False
    
    async def get_arbitrage_whitelist(self) -> Set[str]:
        """Get whitelist for arbitrage strategy"""
        whitelist = set()
        
        for asset in settings.ARBITRAGE_ASSETS:
            if await self.is_tradable(asset):
                whitelist.add(asset)
        
        logger.info(f"Arbitrage whitelist: {whitelist}")
        return whitelist
    
    async def get_meme_whitelist(self) -> Set[str]:
        """Get whitelist for meme strategy"""
        whitelist = set()
        
        for asset in settings.MEME_ASSETS:
            if await self.is_tradable(asset):
                whitelist.add(asset)
        
        logger.info(f"Meme whitelist: {whitelist}")
        return whitelist
    
    async def refresh_all(self):
        """Refresh entire whitelist"""
        logger.info("Refreshing whitelist...")
        
        try:
            async with KrakenFetcher() as fetcher:
                pairs = await fetcher.get_asset_pairs()
                
                if not pairs:
                    logger.warning("No pairs returned from Kraken")
                    return
                
                for pair_name in pairs:
                    for asset in settings.ARBITRAGE_ASSETS + settings.MEME_ASSETS:
                        if pair_name.startswith(asset):
                            self.whitelist.add(asset)
                            if self.redis:
                                try:
                                    await self.redis.setex(
                                        f"tradable:{asset}",
                                        settings.WHITELIST_CACHE_TTL,
                                        "1"
                                    )
                                except Exception as e:
                                    logger.debug(f"Redis cache set failed: {e}")
            
            logger.info(f"Whitelist refreshed: {len(self.whitelist)} assets")
        except Exception as e:
            logger.error(f"Whitelist refresh failed: {e}")
