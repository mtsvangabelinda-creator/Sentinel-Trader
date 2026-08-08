import pandas as pd
from engine.indicators import atr, adx
from strategies.base import Signal


def generate_signals(df_5m: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """
    Always-active strategy: ADX > threshold AND a tight 3-candle consolidation
    (range < consolidation_range_mult * ATR) that then breaks in either direction.
    """
    adx_threshold = cfg["adx_threshold"]
    range_mult = cfg["consolidation_range_mult"]
    stop_mult = cfg["atr_stop_mult"]
    tp_mult = cfg["atr_tp_mult"]

    adx_series = adx(df_5m, period=14)
    atr_series = atr(df_5m, period=14)

    # 3-candle consolidation range (prior 3 candles, excluding current)
    high3 = df_5m["high"].rolling(3).max().shift(1)
    low3 = df_5m["low"].rolling(3).min().shift(1)
    consolidation_range = high3 - low3
    is_tight = consolidation_range < (range_mult * atr_series)

    strong_trend = adx_series > adx_threshold

    breakout_up = (df_5m["close"] > high3) & is_tight & strong_trend
    breakout_down = (df_5m["close"] < low3) & is_tight & strong_trend

    out = pd.DataFrame(index=df_5m.index)
    out["signal"] = (breakout_up | breakout_down).fillna(False)
    out["direction"] = "none"
    out.loc[breakout_up.fillna(False), "direction"] = "long"
    out.loc[breakout_down.fillna(False), "direction"] = "short"

    out["stop_price"] = None
    out.loc[breakout_up.fillna(False), "stop_price"] = (
        df_5m["close"] - stop_mult * atr_series
    )[breakout_up.fillna(False)]
    out.loc[breakout_down.fillna(False), "stop_price"] = (
        df_5m["close"] + stop_mult * atr_series
    )[breakout_down.fillna(False)]

    out["take_profit_price"] = None
    out.loc[breakout_up.fillna(False), "take_profit_price"] = (
        df_5m["close"] + tp_mult * atr_series
    )[breakout_up.fillna(False)]
    out.loc[breakout_down.fillna(False), "take_profit_price"] = (
        df_5m["close"] - tp_mult * atr_series
    )[breakout_down.fillna(False)]

    return out
