"""
Auto-seed OHLCV data from free sources on first run
"""
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from data_harvester.kraken_fetcher import KrakenFetcher
from data_harvester.binance_fetcher import BinanceFetcher
from utils.logger import setup_logger
from config.settings import settings

logger = setup_logger(__name__)

class AutoSeed:
    """Auto-seed historical data"""
    
    @staticmethod
    async def seed_kraken_history(pair: str, days: int = 30) -> bool:
        """Seed Kraken OHLCV for past N days"""
        logger.info(f"Seeding Kraken history for {pair} ({days} days)")
        
        try:
            async with KrakenFetcher() as fetcher:
                data = await fetcher.get_ohlcv(pair, interval=15)
                if data:
                    logger.info(f"Seeded {len(data)} candles for {pair}")
                    return True
            return False
        except Exception as e:
            logger.error(f"Failed to seed Kraken history: {e}")
            return False
    
    @staticmethod
    async def seed_binance_history(symbol: str, days: int = 30) -> bool:
        """Seed Binance history"""
        logger.info(f"Seeding Binance history for {symbol} ({days} days)")
        
        try:
            async with BinanceFetcher() as fetcher:
                data = await fetcher.get_klines(symbol, interval="15m", limit=500)
                if data:
                    logger.info(f"Seeded {len(data)} candles for {symbol}")
                    return True
            return False
        except Exception as e:
            logger.error(f"Failed to seed Binance history: {e}")
            return False
    
    @staticmethod
    async def seed_all() -> bool:
        """Seed all required assets"""
        logger.info("Starting auto-seed...")
        
        all_assets = settings.ARBITRAGE_ASSETS + settings.MEME_ASSETS
        
        tasks = []
        for asset in all_assets:
            kraken_pair = f"{asset}USD"
            binance_symbol = f"{asset}USDT"
            
            tasks.append(AutoSeed.seed_kraken_history(kraken_pair))
            tasks.append(AutoSeed.seed_binance_history(binance_symbol))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if r is True)
        logger.info(f"Seeding complete: {success_count}/{len(results)} succeeded")
        
        return success_count > len(results) / 2
