import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import pandas as pd
import aiohttp

logger = logging.getLogger(__name__)


class KrakenDataFetcher:
    """Fetches multi-timeframe OHLCV data from Kraken API."""
    
    BASE_URL = "https://api.kraken.com/0/public/OHLC"
    MAX_CANDLES_PER_REQUEST = 720  # Kraken limit
    RATE_LIMIT_DELAY = 0.3  # seconds between requests
    
    def __init__(self, pair: str = "XBTUSDT"):
        self.pair = pair
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def get_dataframe(self, days: int = 180, timeframes: list = None) -> Dict[str, pd.DataFrame]:
        """
        Fetch OHLCV data for multiple timeframes.
        
        Args:
            days: Number of days of historical data to fetch
            timeframes: List of timeframes in minutes (e.g., [1, 5, 15])
                       Default: [1, 5, 15] for 1m, 5m, 15m
        
        Returns:
            Dict with keys '1m', '5m', '15m' containing DataFrames with OHLCV data
        """
        if timeframes is None:
            timeframes = [1, 5, 15]
        
        self.session = aiohttp.ClientSession()
        
        try:
            logger.info(f"🌐 Fetching {days} days for timeframes: {timeframes}")
            
            dataframes = {}
            for tf in timeframes:
                logger.info(f"  ⏱️ Fetching {tf}m data...")
                df = await self._fetch_timeframe(days, tf)
                
                if df is None or len(df) < 500:
                    logger.error(f"❌ Insufficient {tf}m data: got {len(df) if df is not None else 0} candles")
                    return None
                
                dataframes[f"{tf}m"] = df
                logger.info(f"  ✅ Loaded {len(df)} {tf}m candles")
                
                # Rate limiting between requests
                await asyncio.sleep(self.RATE_LIMIT_DELAY)
            
            return dataframes
        
        finally:
            if self.session:
                await self.session.close()
    
    async def _fetch_timeframe(self, days: int, interval: int) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV data for a single timeframe.
        
        Kraken returns max 720 candles per request, so we need multiple requests
        for longer periods.
        """
        all_data = []
        
        # Calculate time window
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        # Convert to Unix timestamps
        current_time = int(end_time.timestamp())
        target_time = int(start_time.timestamp())
        
        # Kraken interval in minutes
        kraken_interval = interval
        candles_per_request = self.MAX_CANDLES_PER_REQUEST
        seconds_per_candle = interval * 60
        
        request_count = 0
        max_requests = 500  # Safety limit
        
        while current_time > target_time and request_count < max_requests:
            try:
                params = {
                    'pair': self.pair,
                    'interval': kraken_interval,
                    'since': target_time
                }
                
                async with self.session.get(self.BASE_URL, params=params) as response:
                    if response.status != 200:
                        logger.error(f"Kraken API error {response.status}")
                        await asyncio.sleep(1)
                        continue
                    
                    data = await response.json()
                    
                    if 'result' not in data or not data['result']:
                        logger.warning(f"No data returned for {interval}m interval")
                        break
                    
                    # Kraken returns data with pair as key
                    candles = data['result'].get(self.pair, [])
                    
                    if not candles:
                        break
                    
                    all_data.extend(candles)
                    
                    # Kraken returns data in ascending order
                    # Get the timestamp of the last candle and continue from there
                    last_candle_time = candles[-1][0]
                    current_time = last_candle_time + seconds_per_candle
                    
                    request_count += 1
                    await asyncio.sleep(self.RATE_LIMIT_DELAY)
                    
            except Exception as e:
                logger.error(f"Error fetching {interval}m data: {e}")
                await asyncio.sleep(1)
        
        if not all_data:
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'])
        
        # Clean data types
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        df['open'] = pd.to_numeric(df['open'])
        df['high'] = pd.to_numeric(df['high'])
        df['low'] = pd.to_numeric(df['low'])
        df['close'] = pd.to_numeric(df['close'])
        df['volume'] = pd.to_numeric(df['volume'])
        
        # Set index
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
        
        # Remove duplicates
        df = df[~df.index.duplicated(keep='first')]
        
        return df
