import pandas as pd
from engine.indicators import atr, rsi, bollinger_bands
from strategies.base import Signal


def generate_signals(df_1m: pd.DataFrame, regime_5m: pd.Series, cfg: dict) -> pd.DataFrame:
    """
    df_1m: 1-minute OHLCV.
    regime_5m: regime series computed on 5-min candles; forward-filled onto the
    1-min index so each 1-min bar knows the current 5-min regime.

    Long: RSI < oversold AND close near BB lower band.
    Short: RSI > overbought AND close near BB upper band.
    Active only while regime == 'ranging'.
    """
    rsi_period = cfg["rsi_period"]
    oversold = cfg["rsi_oversold"]
    overbought = cfg["rsi_overbought"]
    stop_mult = cfg["atr_stop_mult"]

    rsi_series = rsi(df_1m, period=rsi_period)
    bb = bollinger_bands(df_1m, period=20, std_mult=2.0)
    atr_series = atr(df_1m, period=14)

    regime_aligned = regime_5m.reindex(df_1m.index, method="ffill")
    ranging = regime_aligned == "ranging"

    near_lower = df_1m["close"] <= bb["bb_lower"]
    near_upper = df_1m["close"] >= bb["bb_upper"]

    long_trigger = (rsi_series < oversold) & near_lower & ranging
    short_trigger = (rsi_series > overbought) & near_upper & ranging

    out = pd.DataFrame(index=df_1m.index)
    out["signal"] = (long_trigger | short_trigger).fillna(False)
    out["direction"] = "none"
    out.loc[long_trigger.fillna(False), "direction"] = "long"
    out.loc[short_trigger.fillna(False), "direction"] = "short"

    out["stop_price"] = None
    out.loc[long_trigger.fillna(False), "stop_price"] = (
        df_1m["close"] - stop_mult * atr_series
    )[long_trigger.fillna(False)]
    out.loc[short_trigger.fillna(False), "stop_price"] = (
        df_1m["close"] + stop_mult * atr_series
    )[short_trigger.fillna(False)]

    # Take profit: BB middle band (mean reversion target)
    out["take_profit_price"] = bb["bb_mid"]
    return out
