import pandas as pd
from engine.indicators import atr, rolling_high
from strategies.base import Signal


def generate_signals(df_5m: pd.DataFrame, regime: pd.Series, cfg: dict) -> pd.DataFrame:
    """
    Long-only breakout: close > highest high of last N candles (N = breakout_period),
    active only while regime == 'trending'.

    Returns a DataFrame indexed same as df_5m with columns:
    signal (bool), direction, stop_price, take_profit_price
    """
    period = cfg["breakout_period"]
    stop_mult = cfg["atr_stop_mult"]
    tp_mult = cfg["atr_tp_mult"]

    hh = rolling_high(df_5m, period)
    atr_series = atr(df_5m, period=14)

    breakout = df_5m["close"] > hh
    trending = regime == "trending"
    triggered = breakout & trending

    stop_price = df_5m["close"] - stop_mult * atr_series
    tp_price = df_5m["close"] + tp_mult * atr_series

    out = pd.DataFrame(index=df_5m.index)
    out["signal"] = triggered.fillna(False)
    out["direction"] = "long"
    out["stop_price"] = stop_price
    out["take_profit_price"] = tp_price
    return out
