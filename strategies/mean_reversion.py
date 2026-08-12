import pandas as pd
import numpy as np
from typing import Optional

from strategies.base import Signal


class MeanReversion:
    """Mean Reversion strategy with multi-timeframe confirmation."""
    
    def __init__(self):
        self.name = "MeanReversion"
        self.rsi_oversold = 35  # Looser than 30
        self.rsi_overbought = 65  # Looser than 70
        self.atr_multiple = 0.4  # Tight stop
        self.lookback_period = 20
    
    def generate_signal(self, df_1m: pd.DataFrame, df_5m: pd.DataFrame, df_15m: pd.DataFrame, regime: str) -> Optional[Signal]:
        """
        Generate signal with 3-timeframe confirmation:
        - 1m: RSI extreme detection
        - 5m: Pullback confirmation
        - 15m: Trend context (mean reversion works best in ranging markets)
        """
        
        if len(df_1m) < 30:
            return None
        
        # ===== 1m: Entry Signal (RSI Extremes) =====
        rsi_1m = self._calculate_rsi(df_1m, period=14)
        latest_rsi = rsi_1m.iloc[-1]
        
        # Detect extreme RSI (oversold or overbought)
        is_oversold = latest_rsi < self.rsi_oversold
        is_overbought = latest_rsi > self.rsi_overbought
        
        if is_oversold:
            action = 'BUY'
            direction_1m = 'UP'
            signal_1m = True
        elif is_overbought:
            action = 'SELL'
            direction_1m = 'DOWN'
            signal_1m = True
        else:
            return None
        
        # ===== 5m: Confirmation (Momentum divergence) =====
        # Check if 5m RSI shows divergence (weaker extreme than 1m)
        rsi_5m = self._calculate_rsi(df_5m, period=14)
        latest_rsi_5m = rsi_5m.iloc[-1]
        prev_rsi_5m = rsi_5m.iloc[-2] if len(rsi_5m) > 1 else latest_rsi_5m
        
        if direction_1m == 'UP':
            # For oversold (buy signal), we want 5m to be recovering
            tf_5m_confirmed = latest_rsi_5m > prev_rsi_5m
        else:
            # For overbought (sell signal), we want 5m to be declining
            tf_5m_confirmed = latest_rsi_5m < prev_rsi_5m
        
        if not tf_5m_confirmed:
            return None
        
        # ===== 15m: Bias (Market regime) =====
        # Mean reversion works best in ranging/neutral markets, not in strong trends
        adx_15m = self._calculate_adx(df_15m, period=14)
        latest_adx_15m = adx_15m.iloc[-1]
        
        # Only trade mean reversion if ADX is low (not trending)
        if latest_adx_15m > 30:
            # Market is trending strongly; mean reversion not ideal
            tf_15m_bias = 'TRENDING'
            return None
        else:
            # Market is ranging/neutral; mean reversion is good
            sma_20_15m = df_15m['close'].rolling(20).mean().iloc[-1]
            current_price_15m = df_15m['close'].iloc[-1]
            
            if current_price_15m > sma_20_15m:
                tf_15m_bias = 'ABOVE_MA'
            else:
                tf_15m_bias = 'BELOW_MA'
        
        # ===== Calculate Entry Details =====
        current_price = df_1m['close'].iloc[-1]
        atr = self._calculate_atr(df_1m, period=14)
        latest_atr = atr.iloc[-1]
        
        entry_price = current_price
        
        # For mean reversion, the target is to return to moving average
        sma_20 = df_1m['close'].rolling(20).mean().iloc[-1]
        
        if action == 'BUY':
            stop_loss = entry_price - (latest_atr * self.atr_multiple)
            # Target: return to 20-SMA or higher
            take_profit = max(sma_20, entry_price + (latest_atr * 1.2))
        else:
            stop_loss = entry_price + (latest_atr * self.atr_multiple)
            # Target: return to 20-SMA or lower
            take_profit = min(sma_20, entry_price - (latest_atr * 1.2))
        
        risk = abs(stop_loss - entry_price)
        reward = abs(take_profit - entry_price)
        risk_reward_ratio = reward / (risk + 1e-8)
        
        # ===== Build Signal =====
        # Confidence based on how extreme the RSI is
        rsi_extremeness = abs(latest_rsi - 50) / 50.0  # 0 to 1
        confidence = min(rsi_extremeness * 0.8 + 0.2, 1.0)
        
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
            reason=f"RSI={latest_rsi:.1f} | ADX15m={latest_adx_15m:.1f} | Target={take_profit:.2f}"
        )
        
        return signal
    
    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / (loss + 1e-8)
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
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
