import logging
import numpy as np

logger = logging.getLogger(__name__)


class MeanReversion:
    """Mean Reversion Strategy - Trades RSI extremes with tight stops."""
    
    def __init__(self, config):
        self.config = config
        self.name = 'mean_reversion'
        self.rsi_period = 7  # REDUCED from 14 (more sensitive)
        self.rsi_oversold = 35  # LOOSENED from 30 (more triggers)
        self.rsi_overbought = 65  # LOOSENED from 70 (more triggers)
    
    def is_active(self, regime):
        """Active in ranging/mean-reversion regimes."""
        return regime in ['ranging', 'trending']
    
    def evaluate(self, candles_1m, candles_5m, ticker):
        """
        Entry: RSI extreme (oversold/overbought) on 1m
        Exit: TIGHT ATR-based stops, quick profits
        """
        
        if len(candles_1m) < self.rsi_period + 5:
            return None
        
        try:
            closes_1m = np.array([c[4] for c in candles_1m])
            highs_5m = np.array([c[2] for c in candles_5m])
            lows_5m = np.array([c[3] for c in candles_5m])
            
            current_price = closes_1m[-1]
            
            # Calculate RSI on 1m
            rsi = self._calculate_rsi(closes_1m, self.rsi_period)
            
            # Calculate ATR from 5m for stops
            atr_values = []
            for i in range(len(candles_5m) - 14, len(candles_5m)):
                h = candles_5m[i][2]
                l = candles_5m[i][3]
                c_prev = candles_5m[i-1][4] if i > 0 else candles_5m[i][4]
                
                tr = max(h - l, abs(h - c_prev), abs(l - c_prev))
                atr_values.append(tr)
            
            atr = np.mean(atr_values)
            
            # Oversold (RSI < 35) → Buy
            if rsi < self.rsi_oversold:
                stop_price = current_price - (atr * 0.4)  # TIGHT: 0.4x ATR
                take_profit = current_price + (atr * 1.0)  # Quick 1x ATR profit
                
                return {
                    'strategy': self.name,
                    'action': 'BUY',
                    'entry_price': current_price,
                    'stop_price': stop_price,
                    'take_profit': take_profit,
                    'confidence': 0.65,
                    'reason': f'RSI oversold ({rsi:.0f})'
                }
            
            # Overbought (RSI > 65) → Sell
            elif rsi > self.rsi_overbought:
                stop_price = current_price + (atr * 0.4)  # TIGHT: 0.4x ATR
                take_profit = current_price - (atr * 1.0)  # Quick 1x ATR profit
                
                return {
                    'strategy': self.name,
                    'action': 'SELL',
                    'entry_price': current_price,
                    'stop_price': stop_price,
                    'take_profit': take_profit,
                    'confidence': 0.65,
                    'reason': f'RSI overbought ({rsi:.0f})'
                }
        
        except Exception as e:
            logger.debug(f"Mean reversion error: {e}")
        
        return None
    
    def _calculate_rsi(self, prices, period):
        """Calculate RSI indicator."""
        deltas = np.diff(prices)
        seed = deltas[:period+1]
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period
        
        rs = up / down if down != 0 else 0
        rsi = 100 - (100 / (1 + rs))
        
        for d in deltas[period+1:]:
            if d >= 0:
                up = (up * (period - 1) + d) / period
                down = down * (period - 1) / period
            else:
                up = up * (period - 1) / period
                down = (down * (period - 1) + (-d)) / period
            
            rs = up / down if down != 0 else 0
            rsi = 100 - (100 / (1 + rs))
        
        return rsi
