import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def atr(candles, period=14):
    """Average True Range from list of candles."""
    try:
        if len(candles) < period + 1:
            return 0
        df = pd.DataFrame(candles, columns=['timestamp','open','high','low','close','volume'])
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        
        tr1 = high - low
        tr2 = np.abs(high - np.roll(close, 1))
        tr3 = np.abs(low - np.roll(close, 1))
        tr = np.max([tr1, tr2, tr3], axis=0)
        
        atr_val = np.mean(tr[-period:])
        return atr_val
    except Exception as e:
        logger.debug(f"ATR error: {e}")
        return 0

def adx(df, period=14):
    """ADX value from DataFrame."""
    try:
        if len(df) < period + 1:
            return 0
        
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        
        plus_dm = np.zeros_like(high)
        minus_dm = np.zeros_like(low)
        
        for i in range(1, len(high)):
            up = high[i] - high[i-1]
            down = low[i-1] - low[i]
            
            if up > down and up > 0:
                plus_dm[i] = up
            if down > up and down > 0:
                minus_dm[i] = down
        
        tr1 = high - low
        tr2 = np.abs(high - np.roll(close, 1))
        tr3 = np.abs(low - np.roll(close, 1))
        tr = np.max([tr1, tr2, tr3], axis=0)
        
        atr_val = np.mean(tr[-period:])
        if atr_val == 0:
            return 0
        
        plus_di = 100 * np.mean(plus_dm[-period:]) / atr_val
        minus_di = 100 * np.mean(minus_dm[-period:]) / atr_val
        
        di_sum = plus_di + minus_di
        if di_sum == 0:
            return 0
        
        dx = 100 * np.abs(plus_di - minus_di) / di_sum
        adx_val = np.mean(np.tile(dx, (period,)))
        
        return adx_val
    except Exception as e:
        logger.debug(f"ADX error: {e}")
        return 0

def rsi(df, period=14):
    """RSI value from DataFrame."""
    try:
        if len(df) < period + 1:
            return 50
        close = df['close'].values
        delta = np.diff(close)
        
        gain = np.zeros_like(delta)
        loss = np.zeros_like(delta)
        
        gain[delta > 0] = delta[delta > 0]
        loss[delta < 0] = -delta[delta < 0]
        
        avg_gain = np.mean(gain[-period:])
        avg_loss = np.mean(loss[-period:])
        
        if avg_loss == 0:
            return 100 if avg_gain > 0 else 50
        
        rs = avg_gain / avg_loss
        rsi_val = 100 - (100 / (1 + rs))
        return rsi_val
    except Exception as e:
        logger.debug(f"RSI error: {e}")
        return 50

def bb(df, period=20, std=2):
    """Bollinger Bands: returns (upper, middle, lower) for latest."""
    try:
        if len(df) < period:
            return None
        close = df['close'].values
        sma = np.mean(close[-period:])
        stddev = np.std(close[-period:])
        upper = sma + std * stddev
        lower = sma - std * stddev
        return upper, sma, lower
    except Exception as e:
        logger.debug(f"BB error: {e}")
        return None
