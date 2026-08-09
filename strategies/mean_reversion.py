import logging
import pandas as pd
from .base import Signal
from engine.indicators import rsi, bb, atr

logger = logging.getLogger(__name__)

class MeanReversion:
    def __init__(self, config):
        self.config = config['strategies']['mean_reversion']
        self.pool = config['strategy_pools']['meanrev']

    def is_active(self, regime):
        return regime == 'ranging'

    def evaluate(self, candles_1m, candles_5m, ticker):
        """1-min RSI(7) oversold/overbought + BB proximity."""
        if len(candles_1m) < 30:
            return None
        
        try:
            df = pd.DataFrame(candles_1m, columns=['timestamp','open','high','low','close','volume'])
            rsi_val = rsi(df, self.config['rsi_period'])
            bb_vals = bb(df, self.config['bb_period'], self.config['bb_std'])
            
            if bb_vals is None:
                return None
            
            upper, middle, lower = bb_vals
            last_close = df['close'].iloc[-1]
            atr_val = atr(candles_1m, 14)
            
            if atr_val == 0:
                return None

            # Long: RSI < oversold and close near lower band
            if rsi_val < self.config['rsi_oversold'] and last_close <= lower * 1.02:
                stop = last_close - self.config['atr_stop_mult'] * atr_val
                tp = middle
                
                return Signal(
                    strategy='meanrev',
                    action='BUY',
                    entry_price=last_close,
                    stop_price=stop,
                    take_profit=tp
                )
            
            # Short: RSI > overbought and close near upper band
            elif rsi_val > self.config['rsi_overbought'] and last_close >= upper * 0.98:
                stop = last_close + self.config['atr_stop_mult'] * atr_val
                tp = middle
                
                return Signal(
                    strategy='meanrev',
                    action='SELL',
                    entry_price=last_close,
                    stop_price=stop,
                    take_profit=tp
                )
        except Exception as e:
            logger.debug(f"MeanRev eval error: {e}")
        
        return None
