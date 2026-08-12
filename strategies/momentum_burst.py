import pandas as pd
import numpy as np
from typing import Optional

from strategies.base import Signal


class MomentumBurst:
    """Momentum Burst strategy with multi-timeframe confirmation."""
    
    def __init__(self):
        self.name = "MomentumBurst"
        self.consolidation_bars = 2  # Tighter consolidation (was 3)
        self.breakout_threshold = 1.02  # 2% above consolidation high
        self.momentum_threshold = 0.5  # Rate of Change threshold
        self.atr_multiple = 0.35  # Stop loss
    
    def generate_signal(self, df_1m: pd.DataFrame, df_5m: pd.DataFrame, df_15m: pd.DataFrame, regime: str) -> Optional[Signal]:
        """
        Generate signal with 3-timeframe confirmation:
        - 1m: Momentum breakout from consolidation
        - 5m: Momentum continuation
        - 15m: Bias filter (avoid trading against the long-term trend)
        """
        
        if len(df_1m) < 30:
            return None
        
        # ===== 1m: Entry Signal (Breakout Detection) =====
        # Find consolidation zone (tight range in last N bars)
        consolidation_period = self.consolidation_bars
        consolidation_data = df_1m['close'].iloc[-consolidation_period:]
        consolidation_high = consolidation_data.max()
        consolidation_low = consolidation_data.min()
        consolidation_range = consolidation_high - consolidation_low
        
        # Check if consolidation is "tight" (small range)
        atr = self._calculate_atr(df_1m, period=14)
        latest_atr = atr.iloc[-1]
        
        if consolidation_range > (latest_atr * 0.5):
            # Range too large; not a tight consolidation
            return None
        
        # Check for breakout
        current_price = df_1m['close'].iloc[-1]
        previous_price = df_1m['close'].iloc[-consolidation_period-1] if len(df_1m) > consolidation_period else df_1m['close'].iloc[-2]
        
        breakout_up = current_price > (consolidation_high * self.breakout_threshold)
        breakout_down = current_price < (consolidation_low / self.breakout_threshold)
        
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
        
        # ===== 1m: Momentum Check =====
        # Confirm momentum is accelerating
        roc = self._calculate_roc(df_1m, period=14)
        latest_roc = roc.iloc[-1]
        
        if direction_1m == 'UP' and latest_roc < self.momentum_threshold:
            # Breakout but no momentum
            return None
        elif direction_1m == 'DOWN' and latest_roc > -self.momentum_threshold:
            # Breakout but no momentum
            return None
        
        # ===== 5m: Confirmation (Momentum continuation) =====
        rsi_5m = self._calculate_rsi(df_5m, period=14)
        latest_rsi_5m = rsi_5m.iloc[-1]
        
        if direction_1m == 'UP':
            # For upside breakout, 5m RSI should be elevated (>50)
            tf_5m_confirmed = latest_rsi_5m > 50
        else:
            # For downside breakout, 5m RSI should be depressed (<50)
            tf_5m_confirmed = latest_rsi_5m < 50
        
        if not tf_5m_confirmed:
            return None
        
        # ===== 15m: Bias Filter =====
        # Only trade momentum in direction aligned with 15m trend
        sma_50_15m = df_15m['close'].rolling(50).mean().iloc[-1]
        current_price_15m = df_15m['close'].iloc[-1]
        
        if direction_1m == 'UP':
            # For upside momentum, prefer when 15m is in uptrend
            if current_price_15m < sma_50_15m:
                tf_15m_bias = 'DOWNTREND'
                return None  # Don't trade breakup in downtrend
            else:
                tf_15m_bias = 'UPTREND'
        else:
            # For downside momentum, prefer when 15m is in downtrend
            if current_price_15m > sma_50_15m:
                tf_15m_bias = 'UPTREND'
                return None  # Don't trade breakdown in uptrend
            else:
                tf_15m_bias = 'DOWNTREND'
        
        # ===== Calculate Entry Details =====
        entry_price = current_price
        
        if action == 'BUY':
            stop_loss = consolidation_low - (latest_atr * self.atr_multiple)
            take_profit = entry_price + (latest_atr * 2.0)
        else:
            stop_loss = consolidation_high + (latest_atr * self.atr_multiple)
            take_profit = entry_price - (latest_atr * 2.0)
        
        risk = abs(stop_loss - entry_price)
        reward = abs(take_profit - entry_price)
        risk_reward_ratio = reward / (risk + 1e-8)
        
        # ===== Build Signal =====
        # Confidence based on momentum strength
        roc_extremeness = abs(latest_roc / 2.0)  # Normalize
        confidence = min(roc_extremeness * 0.7 + 0.3, 1.0)
        
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
            reason=f"Breakout from {consolidation_range:.2f} consolidation | ROC={latest_roc:.2f} | RR={risk_reward_ratio:.2f}"
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
    
    def _calculate_roc(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Rate of Change."""
        roc = ((df['close'] - df['close'].shift(period)) / df['close'].shift(period)) * 100
        return roc
    
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
