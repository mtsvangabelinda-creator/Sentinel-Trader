import logging
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)


class VolatilityBreakout:
    """Volatility Breakout Strategy - Trades when volatility spikes."""
    
    def __init__(self, config):
        self.config = config
        self.name = 'volatility_breakout'
        self.volatility_lookback = 14
        self.volatility_multiplier = 1.5  # Trigger when vol > 1.5x average
        self.breakout_threshold = 0.15  # 0.15% move
    
    def is_active(self, regime):
        """Always active - works in all regimes."""
        return True
    
    def evaluate(self, candles_1m, candles_5m, ticker):
        """
        Volatility breakout logic:
        
        1. Calculate 14-period ATR (volatility)
        2. If current ATR > 1.5x average ATR, volatility is spiking
        3. If price breaks above/below recent high/low, enter
        """
        
        if len(candles_5m) < self.volatility_lookback + 5:
            return None
        
        try:
            # Extract OHLCV from 5m candles
            closes = np.array([c[4] for c in candles_5m])
            highs = np.array([c[2] for c in candles_5m])
            lows = np.array([c[3] for c in candles_5m])
            
            current_price = closes[-1]
            
            # Calculate ATR (True Range)
            tr1 = highs[-1] - lows[-1]
            tr2 = abs(highs[-1] - closes[-2])
            tr3 = abs(lows[-1] - closes[-2])
            tr = max(tr1, tr2, tr3)
            
            # Calculate average ATR
            atr_values = []
            for i in range(len(candles_5m) - self.volatility_lookback, len(candles_5m)):
                h = candles_5m[i][2]
                l = candles_5m[i][3]
                c_prev = candles_5m[i-1][4] if i > 0 else candles_5m[i][4]
                
                tr_i = max(
                    h - l,
                    abs(h - c_prev),
                    abs(l - c_prev)
                )
                atr_values.append(tr_i)
            
            avg_atr = np.mean(atr_values)
            
            # Check if volatility is spiking
            vol_spike = tr > (avg_atr * self.volatility_multiplier)
            
            if not vol_spike:
                return None
            
            # Calculate recent high/low for breakout
            recent_high = np.max(highs[-10:])
            recent_low = np.min(lows[-10:])
            
            # Breakout entry logic
            entry_price = current_price
            
            # Long breakout (above recent high)
            if current_price > recent_high * (1 + self.breakout_threshold / 100):
                stop_price = recent_low - (avg_atr * 0.5)  # TIGHT stop
                take_profit = current_price + (avg_atr * 2)
                
                return {
                    'strategy': self.name,
                    'action': 'BUY',
                    'entry_price': entry_price,
                    'stop_price': stop_price,
                    'take_profit': take_profit,
                    'confidence': 0.7,
                    'reason': 'Volatility spike + breakout above recent high'
                }
            
            # Short breakout (below recent low)
            elif current_price < recent_low * (1 - self.breakout_threshold / 100):
                stop_price = recent_high + (avg_atr * 0.5)  # TIGHT stop
                take_profit = current_price - (avg_atr * 2)
                
                return {
                    'strategy': self.name,
                    'action': 'SELL',
                    'entry_price': entry_price,
                    'stop_price': stop_price,
                    'take_profit': take_profit,
                    'confidence': 0.7,
                    'reason': 'Volatility spike + breakout below recent low'
                }
        
        except Exception as e:
            logger.debug(f"Volatility breakout error: {e}")
        
        return None
