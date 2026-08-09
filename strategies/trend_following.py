import logging
import pandas as pd
from .base import Signal
from engine.indicators import atr

logger = logging.getLogger(__name__)

class TrendFollowing:
    def __init__(self, config):
        self.config = config['strategies']['trend_following']
        self.pool = config['strategy_pools']['trend']

    def is_active(self, regime):
        return regime == 'trending'

    def evaluate(self, candles_1m, candles_5m, ticker):
        """5-min breakout: close > highest high of last N candles."""
        if len(candles_5m) < self.config['breakout_period'] + 2:
            return None
        
        try:
            df = pd.DataFrame(candles_5m, columns=['timestamp','open','high','low','close','volume'])
            last_close = df['close'].iloc[-1]
            
            # Get highest high from last N candles (excluding current)
            period = self.config['breakout_period']
            highest_high = df['high'].iloc[-period-1:-1].max()
            
            if last_close > highest_high:
                atr_val = atr(candles_5m, 14)
                if atr_val == 0:
                    return None
                
                stop = last_close - self.config['atr_stop_mult'] * atr_val
                tp = last_close + self.config['atr_tp_mult'] * atr_val
                
                return Signal(
                    strategy='trend',
                    action='BUY',
                    entry_price=last_close,
                    stop_price=stop,
                    take_profit=tp
                )
        except Exception as e:
            logger.debug(f"Trend eval error: {e}")
        
        return None
