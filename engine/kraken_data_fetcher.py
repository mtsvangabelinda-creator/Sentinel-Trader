import asyncio
import logging
import ccxt.async_support as ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class KrakenDataFetcher:
    """Fetch OHLCV data from Kraken API with proper rate limiting."""
    
    def __init__(self):
        self.exchange = ccxt.kraken({'enableRateLimit': True})
        self.symbol = 'BTC/USD'
    
    async def fetch_historical_ohlcv(self, days=180, timeframe='1m'):
        """Fetch last N days of OHLCV data from Kraken with robust rate limiting."""
        try:
            logger.info(f"📥 Fetching {days} days of {timeframe} candles from Kraken...")
            
            since = int((datetime.utcnow() - timedelta(days=days)).timestamp() * 1000)
            all_ohlcv = []
            batch_count = 0
            consecutive_errors = 0
            
            while since < int(datetime.utcnow().timestamp() * 1000):
                try:
                    logger.debug(f"Fetching batch {batch_count + 1}...")
                    ohlcv = await self.exchange.fetch_ohlcv(
                        self.symbol,
                        timeframe=timeframe,
                        since=since,
                        limit=720
                    )
                    
                    if not ohlcv or len(ohlcv) == 0:
                        logger.info("No more data available from Kraken")
                        break
                    
                    all_ohlcv.extend(ohlcv)
                    batch_count += 1
                    consecutive_errors = 0
                    
                    # Update since for next batch
                    since = int(ohlcv[-1][0]) + 60000
                    
                    # Better rate limiting - Kraken allows ~15 calls per second
                    await asyncio.sleep(0.5)
                    
                except ccxt.RateLimitExceeded:
                    consecutive_errors += 1
                    if consecutive_errors > 3:
                        logger.warning("Too many rate limit errors, stopping fetch")
                        break
                    logger.warning(f"Rate limit hit, backing off... (attempt {consecutive_errors}/3)")
                    await asyncio.sleep(2)
                except ccxt.NetworkError as e:
                    consecutive_errors += 1
                    if consecutive_errors > 3:
                        logger.warning("Too many network errors, stopping fetch")
                        break
                    logger.warning(f"Network error: {e}, retrying... (attempt {consecutive_errors}/3)")
                    await asyncio.sleep(2)
                except Exception as e:
                    consecutive_errors += 1
                    if consecutive_errors > 3:
                        logger.warning("Too many errors, stopping fetch")
                        break
                    logger.warning(f"Fetch batch error: {e}, retrying...")
                    await asyncio.sleep(1)
            
            logger.info(f"✅ Fetched {len(all_ohlcv)} candles in {batch_count} batches")
            
            if len(all_ohlcv) == 0:
                logger.error("No OHLCV data retrieved from Kraken")
                return None
            
            return all_ohlcv
        
        except Exception as e:
            logger.error(f"Kraken fetch error: {e}")
            return None
    
    async def get_dataframe(self, days=60, timeframe='1m'):
        """Get OHLCV data as DataFrame."""
        ohlcv = await self.fetch_historical_ohlcv(days=days, timeframe=timeframe)
        
        if ohlcv is None or len(ohlcv) == 0:
            logger.error("Failed to get OHLCV data")
            return None
        
        try:
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Remove duplicates
            df = df.drop_duplicates(subset=['timestamp'], keep='first')
            
            # Sort by timestamp
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            logger.info(f"DataFrame created: {len(df)} rows from {df['timestamp'].min()} to {df['timestamp'].max()}")
            return df
        
        except Exception as e:
            logger.error(f"DataFrame creation error: {e}")
            return None
    
    async def get_candles_list(self, days=60, timeframe='1m'):
        """Get candles as list format [[ts, open, high, low, close, volume], ...]"""
        df = await self.get_dataframe(days=days, timeframe=timeframe)
        
        if df is None:
            return None
        
        candles = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].values.tolist()
        return candles
