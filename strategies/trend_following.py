import pandas as pd
import numpy as np
from typing import Optional

from strategies.base import Signal


class TrendFollowing:
    """Trend Following strategy with multi-timeframe confirmation."""
    
    def __init__(self):
        self.name = "TrendFollowing"
        self.lookback_period = 8  # Aggressive: 8 instead of 20
        self.adx_threshold = 20  # ADX > 20 = trending
        self.atr_multiple = 0.3  # Stop loss: 0.3x ATR
    
    def generate_signal(self, df_1m: pd.DataFrame, df_5m: pd.DataFrame, df_15m: pd.DataFrame, regime: str) -> Optional[Signal]:
        """
        Generate signal with 3-timeframe confirmation:
        - 1m: ADX breakout detection
        - 5m: Momentum confirmation
        - 15m: Market bias (uptrend/downtrend)
        """
        
        if len(df_1m) < self.lookback_period + 20:
            return None
        
        # ===== 1m: Entry Signal =====
        adx_1m = self._calculate_adx(df_1m, period=14)
        latest_adx = adx_1m.iloc[-1]
        
        # Check if ADX just crossed above threshold (trend starting)
        prev_adx = adx_1m.iloc[-2] if len(adx_1m) > 1 else 0
        adx_crossover = prev_adx < self.adx_threshold and latest_adx >= self.adx_threshold
        
        # Determine direction from price action
        recent_high = df_1m['high'].iloc[-self.lookback_period:].max()
        recent_low = df_1m['low'].iloc[-self.lookback_period:].min()
        current_price = df_1m['close'].iloc[-1]
        
        is_bullish = current_price > recent_high * 0.99  # Near recent highs
        is_bearish = current_price < recent_low * 1.01   # Near recent lows
        
        signal_1m = adx_crossover and (is_bullish or is_bearish)
        direction_1m = 'UP' if is_bullish else ('DOWN' if is_bearish else 'NEUTRAL')
        
        if not signal_1m or direction_1m == 'NEUTRAL':
            return None
        
        # ===== 5m: Confirmation =====
        # Check if 5m momentum confirms the direction
        rsi_5m = self._calculate_rsi(df_5m, period=14)
        latest_rsi_5m = rsi_5m.iloc[-1]
        
        if direction_1m == 'UP':
            tf_5m_confirmed = latest_rsi_5m > 40  # Not oversold, bullish bias
        else:
            tf_5m_confirmed = latest_rsi_5m < 60  # Not overbought, bearish bias
        
        if not tf_5m_confirmed:
            return None
        
        # ===== 15m: Bias =====
        # Determine market bias from 15m: is overall trend up or down?
        sma_20_15m = df_15m['close'].rolling(20).mean().iloc[-1]
        current_price_15m = df_15m['close'].iloc[-1]
        
        if current_price_15m > sma_20_15m:
            tf_15m_bias = 'UP'
        elif current_price_15m < sma_20_15m:
            tf_15m_bias = 'DOWN'
        else:
            tf_15m_bias = 'NEUTRAL'
        
        # Only trade if 1m direction aligns with 15m bias
        if direction_1m == 'UP' and tf_15m_bias != 'UP':
            return None
        if direction_1m == 'DOWN' and tf_15m_bias != 'DOWN':
            return None
        
        # ===== Calculate Entry Details =====
        atr = self._calculate_atr(df_1m, period=14)
        latest_atr = atr.iloc[-1]
        
        entry_price = current_price
        
        if direction_1m == 'UP':
            stop_loss = entry_price - (latest_atr * self.atr_multiple)
            take_profit = entry_price + (latest_atr * 1.5)
            action = 'BUY'
        else:
            stop_loss = entry_price + (latest_atr * self.atr_multiple)
            take_profit = entry_price - (latest_atr * 1.5)
            action = 'SELL'
        
        risk = abs(stop_loss - entry_price)
        reward = abs(take_profit - entry_price)
        risk_reward_ratio = reward / (risk + 1e-8)
        
        # ===== Build Signal =====
        confidence = min(latest_adx / 50.0, 1.0)  # Higher ADX = more confident
        
        signal = Signal(
            action=action,
            confidence=confidence,
            tf_1m_signal=signal_1m,
            tf_5m_confirmed=tf_5m_confirmed,
            tf_15m_bias=tf_15m_bias,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=risk_reward_ratio,
            strategy_name=self.name,
            reason=f"ADX={latest_adx:.1f} | Bias={tf_15m_bias} | RSI5m={latest_rsi_5m:.1f}"
        )
        
        return signal
    
    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average Directional Index."""
        high = df['high']
        low = df['low']
        close = df['close']
        
        plus_dm = np.where((high.diff() > low.diff().abs()) & (high.diff() > 0), high.diff(), 0)
        minus_dm = np.where((low.diff().abs() > high.diff()) & (low.diff() < 0), low.diff().abs(), 0)
        
        tr = np.maximum(
            high.diff().abs(),
            np.maximum(
                (high - close.shift()).abs(),
                (low - close.shift()).abs()
            )
        )
        
        atr = pd.Series(tr).rolling(period).mean()
        
        plus_di = 100 * pd.Series(plus_dm).rolling(period).mean() / (atr + 1e-8)
        minus_di = 100 * pd.Series(minus_dm).rolling(period).mean() / (atr + 1e-8)
        
        di_diff = (plus_di - minus_di).abs()
        di_sum = plus_di + minus_di
        
        adx = 100 * di_diff / (di_sum + 1e-8)
        adx = pd.Series(adx).rolling(period).mean()
        
        return adx
    
    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / (loss + 1e-8)
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr = np.maximum(
            high - low,
            np.maximum(
                (high - close.shift()).abs(),
                (low - close.shift()).abs()
            )
        )
        
        atr = pd.Series(tr).rolling(period).mean()
        return atr
