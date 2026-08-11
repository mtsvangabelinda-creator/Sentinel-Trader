import logging
import numpy as np

logger = logging.getLogger(__name__)


class MomentumBurst:
    """Momentum Burst Strategy - Trades consolidation breakouts."""
    
    def __init__(self, config):
        self.config = config
        self.name = 'momentum_burst'
        self.consolidation_bars = 2  # REDUCED from 3 (more frequent)
        self.roc_period = 5
        self.roc_threshold = 0.5  # LOOSENED from 1.0 (more triggers)
    
    def is_active(self, regime):
        """Always active."""
        return True
    
    def evaluate(self, candles_1m, candles_5m, ticker):
        """
        Entry: After consolidation (tight range), momentum break
        Exit: TIGHT ATR stops, quick profits
        """
        
        if len(candles_5m) < self.consolidation_bars + 5:
            return None
        
        try:
            closes = np.array([c[4] for c in candles_5m])
            highs = np.array([c[2] for c in candles_5m])
            lows = np.array([c[3] for c in candles_5m])
            
            current_price = closes[-1]
            
            # Check for consolidation (tight range)
            recent_range = np.max(highs[-self.consolidation_bars:]) - np.min(lows[-self.consolidation_bars:])
            avg_range = np.mean([highs[i] - lows[i] for i in range(-self.consolidation_bars-5, -self.consolidation_bars)])
            
            is_consolidating = recent_range < (avg_range * 0.7)
            
            if not is_consolidating:
                return None
            
            # Calculate ROC (rate of change)
            roc = ((closes[-1] - closes[-self.roc_period]) / closes[-self.roc_period]) * 100
            
            # Calculate ATR
            atr_values = []
            for i in range(len(candles_5m) - 14, len(candles_5m)):
                h = candles_5m[i][2]
                l = candles_5m[i][3]
                c_prev = candles_5m[i-1][4] if i > 0 else candles_5m[i][4]
                
                tr = max(h - l, abs(h - c_prev), abs(l - c_prev))
                atr_values.append(tr)
            
            atr = np.mean(atr_values)
            
            # Upside momentum
            if roc > self.roc_threshold:
                stop_price = current_price - (atr * 0.35)  # TIGHT: 0.35x ATR
                take_profit = current_price + (atr * 1.2)  # Quick 1.2x ATR
                
                return {
                    'strategy': self.name,
                    'action': 'BUY',
                    'entry_price': current_price,
                    'stop_price': stop_price,
                    'take_profit': take_profit,
                    'confidence': 0.7,
                    'reason': f'Consolidation breakout (ROC: {roc:.1f}%)'
                }
            
            # Downside momentum
            elif roc < -self.roc_threshold:
                stop_price = current_price + (atr * 0.35)  # TIGHT: 0.35x ATR
                take_profit = current_price - (atr * 1.2)  # Quick 1.2x ATR
                
                return {
                    'strategy': self.name,
                    'action': 'SELL',
                    'entry_price': current_price,
                    'stop_price': stop_price,
                    'take_profit': take_profit,
                    'confidence': 0.7,
                    'reason': f'Consolidation breakout (ROC: {roc:.1f}%)'
                }
        
        except Exception as e:
            logger.debug(f"Momentum burst error: {e}")
        
        return None
