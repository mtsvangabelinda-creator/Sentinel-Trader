"""
The Sentinel is a pure safety gate. It never generates signals and never
closes positions -- it only blocks NEW entries when conditions look toxic
(wide spread, or a candle range blown out relative to recent volatility).

In backtesting we don't have live bid/ask, so spread is estimated as a
constant historical average unless real order-book data is supplied.
"""
import pandas as pd
from engine.indicators import atr


def sentinel_mask(df: pd.DataFrame, max_spread_pct: float = 0.05,
                   max_range_atr_mult: float = 3.0,
                   estimated_spread_pct: float = 0.02) -> pd.Series:
    """
    Returns a boolean Series: True = safe to enter, False = blocked.
    df must have high/low/close columns.
    """
    atr_series = atr(df, period=14)
    candle_range = df["high"] - df["low"]

    range_ok = candle_range <= (max_range_atr_mult * atr_series)
    spread_ok = estimated_spread_pct <= max_spread_pct  # constant in backtest

    safe = range_ok & spread_ok
    return safe.fillna(False)
