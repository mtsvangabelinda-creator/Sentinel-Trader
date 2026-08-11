import logging
import numpy as np

logger = logging.getLogger(__name__)


class TrendFollowing:
    """Trend Following Strategy - Breakout above/below recent highs/lows."""
    
    def __init__(self, config):
        self.config = config
        self.name = 'trend_following'
        self.lookback = 8  # REDUCED from 20 (more aggressive)
        self.atr_period = 14
    
    def is_active(self, regime):
        """Active in trending regimes."""
        return regime == 'trending'
    
    def evaluate(self, candles_1m, candles_5m, ticker):
        """
        Entry: Close above highest high of last N candles
        Exit: ATR-based stop (tight) and 2x ATR take profit
        """
        
        if len(candles_5m) < self.lookback + 5:
            return None
        
        try:
            closes = np.array([c[4] for c in candles_5m])
            highs = np.array([c[2] for c in candles_5m])
            lows = np.array([c[3] for c in candles_5m])
            
            current_price = closes[-1]
            
            # Calculate ATR
            atr_values = []
            for i in range(len(candles_5m) - self.atr_period, len(candles_5m)):
                h = candles_5m[i][2]
                l = candles_5m[i][3]
                c_prev = candles_5m[i-1][4] if i > 0 else candles_5m[i][4]
                
                tr = max(
                    h - l,
                    abs(h - c_prev),
                    abs(l - c_prev)
                )
                atr_values.append(tr)
            
            atr = np.mean(atr_values)
            
            # Get recent high/low
            recent_high = np.max(highs[-self.lookback:])
            recent_low = np.min(lows[-self.lookback:])
            
            # Long: breakout above recent high
            if current_price > recent_high:
                stop_price = recent_low - (atr * 0.3)  # TIGHT: 0.3x ATR
                take_profit = current_price + (atr * 1.5)  # 1.5x ATR target
                
                return {
                    'strategy': self.name,
                    'action': 'BUY',
                    'entry_price': current_price,
                    'stop_price': stop_price,
                    'take_profit': take_profit,
                    'confidence': 0.6,
                    'reason': f'Breakout above {self.lookback}-bar high'
                }
            
            # Short: breakout below recent low
            elif current_price < recent_low:
                stop_price = recent_high + (atr * 0.3)  # TIGHT: 0.3x ATR
                take_profit = current_price - (atr * 1.5)  # 1.5x ATR target
                
                return {
                    'strategy': self.name,
                    'action': 'SELL',
                    'entry_price': current_price,
                    'stop_price': stop_price,
                    'take_profit': take_profit,
                    'confidence': 0.6,
                    'reason': f'Breakout below {self.lookback}-bar low'
                }
        
        except Exception as e:
            logger.debug(f"Trend following error: {e}")
        
        return None
