import pandas as pd
import numpy as np
from typing import Optional

from strategies.base import Signal


class VolatilityBreakout:
    """Volatility Breakout strategy with multi-timeframe confirmation."""
    
    def __init__(self):
        self.name = "VolatilityBreakout"
        self.volatility_threshold = 1.2  # Breakout when volatility exceeds 1.2x average
        self.bollinger_period = 20
        self.bollinger_std = 2.0
        self.atr_multiple = 0.35  # Tight stop loss
    
    def generate_signal(self, df_1m: pd.DataFrame, df_5m: pd.DataFrame, df_15m: pd.DataFrame, regime: str) -> Optional[Signal]:
        """
        Generate signal with 3-timeframe confirmation:
        - 1m: Bollinger Band breakout on high volatility
        - 5m: Volatility confirmation (elevated vol on 5m too)
        - 15m: Vol regime (only trade high vol breakouts when vol context allows)
        """
        
        if len(df_1m) < self.bollinger_period + 10:
            return None
        
        # ===== 1m: Entry Signal (Bollinger Band Breakout) =====
        sma = df_1m['close'].rolling(self.bollinger_period).mean()
        std = df_1m['close'].rolling(self.bollinger_period).std()
        
        upper_band = sma + (std * self.bollinger_std)
        lower_band = sma - (std * self.bollinger_std)
        
        current_price = df_1m['close'].iloc[-1]
        previous_price = df_1m['close'].iloc[-2]
        
        # Check for breakout through bands
        breakout_up = (previous_price <= upper_band.iloc[-2]) and (current_price > upper_band.iloc[-1])
        breakout_down = (previous_price >= lower_band.iloc[-2]) and (current_price < lower_band.iloc[-1])
        
        if breakout_up:
            action = 'BUY'
            direction_1m = 'UP'
            signal_1m = True
        elif breakout_down:
            action = 'SELL'
            direction_1m = 'DOWN'
            signal_1m = True
        else:
            return None
        
        # ===== 1m: Volatility Check =====
        atr = self._calculate_atr(df_1m, period=14)
        latest_atr = atr.iloc[-1]
        avg_atr = atr.iloc[-20:].mean()
        
        # Only trade if volatility is elevated
        volatility_ratio = latest_atr / (avg_atr + 1e-8)
        if volatility_ratio < self.volatility_threshold:
            # Not enough volatility expansion
            return None
        
        # ===== 5m: Volatility Confirmation =====
        # Confirm that 5m volatility is also elevated
        atr_5m = self._calculate_atr(df_5m, period=14)
        latest_atr_5m = atr_5m.iloc[-1]
        avg_atr_5m = atr_5m.iloc[-20:].mean()
        
        volatility_ratio_5m = latest_atr_5m / (avg_atr_5m + 1e-8)
        tf_5m_confirmed = volatility_ratio_5m > 1.0  # Any elevation is good
        
        if not tf_5m_confirmed:
            return None
        
        # ===== 15m: Volatility Regime =====
        # Check if high volatility is sustainable on 15m
        atr_15m = self._calculate_atr(df_15m, period=14)
        latest_atr_15m = atr_15m.iloc[-1]
        avg_atr_15m = atr_15m.iloc[-30:].mean()
        
        volatility_ratio_15m = latest_atr_15m / (avg_atr_15m + 1e-8)
        
        if volatility_ratio_15m > 1.3:
            tf_15m_bias = 'HIGH_VOL'  # Sustained high vol environment
        elif volatility_ratio_15m > 1.0:
            tf_15m_bias = 'ELEVATED_VOL'  # Moderately elevated
        else:
            tf_15m_bias = 'LOW_VOL'  # Vol is recovering
            # Don't trade vol breakouts in low vol regime
            return None
        
        # ===== Calculate Entry Details =====
        entry_price = current_price
        
        if action == 'BUY':
            stop_loss = entry_price - (latest_atr * self.atr_multiple)
            # Target: 2x the ATR expansion
            take_profit = entry_price + (latest_atr * 2.0)
        else:
            stop_loss = entry_price + (latest_atr * self.atr_multiple)
            # Target: 2x the ATR expansion
            take_profit = entry_price - (latest_atr * 2.0)
        
        risk = abs(stop_loss - entry_price)
        reward = abs(take_profit - entry_price)
        risk_reward_ratio = reward / (risk + 1e-8)
        
        # ===== Build Signal =====
        # Confidence based on volatility expansion strength
        vol_confidence = min(volatility_ratio / 2.0, 1.0)
        confidence = min(vol_confidence * 0.8 + 0.2, 1.0)
        
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
            reason=f"BB Breakout | Vol Ratio={volatility_ratio:.2f} | Regime={tf_15m_bias}"
        )
        
        return signal
    
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
