import asyncio
import json
import logging
import time
from collections import deque
from typing import Optional, Dict, List

import ccxt.async_support as ccxt
import websockets
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class DataFeed:
    """Real-time data feed from Kraken WebSocket with REST fallback."""
    def __init__(self, config, db):
        self.config = config
        self.db = db
        self.exchange = ccxt.kraken({'enableRateLimit': True})
        self.ws_url = "wss://ws.kraken.com/v2"
        self.connected = False
        self.ticker = {}
        self.candles = {
            '1m': deque(maxlen=1000),
            '5m': deque(maxlen=1000)
        }
        self.last_rest_update = 0
        self._ws_task = None

    async def start(self):
        """Start WebSocket connection and maintain it."""
        self._ws_task = asyncio.create_task(self._ws_loop())
        asyncio.create_task(self._rest_fallback())

    async def _ws_loop(self):
        """Maintain WebSocket connection with reconnection."""
        while True:
            try:
                async with websockets.connect(self.ws_url, ping_interval=30) as ws:
                    self.connected = True
                    logger.info("WebSocket connected")
                    
                    # Subscribe
                    subscribe_msg = {
                        "method": "subscribe",
                        "params": {
                            "channel": "ticker",
                            "symbol": ["BTC/USD"]
                        }
                    }
                    await ws.send(json.dumps(subscribe_msg))
                    
                    for interval in ['1m', '5m']:
                        sub_ohlc = {
                            "method": "subscribe",
                            "params": {
                                "channel": "ohlc",
                                "symbol": ["BTC/USD"],
                                "interval": interval
                            }
                        }
                        await ws.send(json.dumps(sub_ohlc))
                    
                    async for message in ws:
                        try:
                            data = json.loads(message)
                            await self._process_message(data)
                        except json.JSONDecodeError:
                            pass
            except Exception as e:
                logger.warning(f"WebSocket error: {e}")
                self.connected = False
                await asyncio.sleep(5)

    async def _process_message(self, data):
        """Process incoming WebSocket messages."""
        try:
            if 'channel' in data:
                if data['channel'] == 'ticker' and 'data' in data:
                    ticker_data = data['data'][0]
                    self.ticker = {
                        'bid': float(ticker_data['bid']),
                        'ask': float(ticker_data['ask']),
                        'last': float(ticker_data['last']),
                        'timestamp': int(time.time() * 1000)
                    }
                elif data['channel'] == 'ohlc' and 'data' in data:
                    for ohlc in data['data']:
                        interval = ohlc.get('interval', '1m')
                        ts = int(float(ohlc['timestamp']) * 1000)
                        open_ = float(ohlc['open'])
                        high = float(ohlc['high'])
                        low = float(ohlc['low'])
                        close = float(ohlc['close'])
                        volume = float(ohlc['volume'])
                        candle = [ts, open_, high, low, close, volume]
                        
                        if interval == '1m':
                            self.candles['1m'].append(candle)
                        elif interval == '5m':
                            self.candles['5m'].append(candle)
                        
                        self.db.insert_candle(interval, candle)
        except (KeyError, ValueError, TypeError) as e:
            logger.debug(f"Message processing error: {e}")

    async def _rest_fallback(self):
        """Fetch ticker via REST if WebSocket is down or to backfill candles."""
        while True:
            try:
                await asyncio.sleep(5)
                if not self.connected or len(self.candles['1m']) < 10:
                    ticker = await self.exchange.fetch_ticker('BTC/USD')
                    self.ticker = {
                        'bid': ticker['bid'],
                        'ask': ticker['ask'],
                        'last': ticker['last'],
                        'timestamp': int(ticker['timestamp'])
                    }
                    
                    if len(self.candles['1m']) < 100:
                        ohlcv_1m = await self.exchange.fetch_ohlcv('BTC/USD', '1m', limit=300)
                        for candle in ohlcv_1m[-200:]:
                            if list(candle) not in list(self.candles['1m']):
                                self.candles['1m'].append(candle)
                    
                    if len(self.candles['5m']) < 100:
                        ohlcv_5m = await self.exchange.fetch_ohlcv('BTC/USD', '5m', limit=300)
                        for candle in ohlcv_5m[-200:]:
                            if list(candle) not in list(self.candles['5m']):
                                self.candles['5m'].append(candle)
            except Exception as e:
                logger.debug(f"REST fallback error: {e}")
                await asyncio.sleep(5)

    def get_ticker(self):
        return self.ticker if self.ticker else None

    def get_candles(self, interval):
        """Return list of candles as [[ts, open, high, low, close, volume], ...]."""
        return list(self.candles.get(interval, []))

    def get_latest_candle(self, interval):
        candles = self.candles.get(interval, [])
        return candles[-1] if candles else None
