import logging
import pandas as pd
from .base import Signal
from engine.indicators import adx, atr

logger = logging.getLogger(__name__)

class MomentumBurst:
    def __init__(self, config):
        self.config = config['strategies']['momentum_burst']
        self.pool = config['strategy_pools']['momentum']

    def is_active(self, regime):
        return True  # Always active

    def evaluate(self, candles_1m, candles_5m, ticker):
        """ADX>threshold & tight consolidation breakout."""
        if len(candles_5m) < 25:
            return None
        
        try:
            df = pd.DataFrame(candles_5m, columns=['timestamp','open','high','low','close','volume'])
            adx_val = adx(df, 14)
            
            if adx_val < self.config['adx_threshold']:
                return None
            
            # Check last 3 candles for consolidation
            last_3 = df.tail(3)
            high_max = last_3['high'].max()
            low_min = last_3['low'].min()
            range_3 = high_max - low_min
            
            atr_val = atr(candles_5m, 14)
            if atr_val == 0:
                return None
            
            # Consolidation should be tight
            if range_3 > self.config['consolidation_range'] * atr_val:
                return None
            
            last_close = df['close'].iloc[-1]
            
            # Breakout above 3-candle high
            if last_close > high_max:
                stop = last_close - self.config['atr_stop_mult'] * atr_val
                tp = last_close + self.config['atr_tp_mult'] * atr_val
                
                return Signal(
                    strategy='momentum',
                    action='BUY',
                    entry_price=last_close,
                    stop_price=stop,
                    take_profit=tp
                )
            
            # Breakout below 3-candle low
            elif last_close < low_min:
                stop = last_close + self.config['atr_stop_mult'] * atr_val
                tp = last_close - self.config['atr_tp_mult'] * atr_val
                
                return Signal(
                    strategy='momentum',
                    action='SELL',
                    entry_price=last_close,
                    stop_price=stop,
                    take_profit=tp
                )
        except Exception as e:
            logger.debug(f"Momentum eval error: {e}")
        
        return None
