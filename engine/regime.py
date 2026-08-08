"""
Classifies each 5-min candle as 'trending' or 'ranging' based on ADX(14),
with a persistence filter so the regime doesn't flip on a single noisy candle.
"""
import pandas as pd
from engine.indicators import adx


def classify_regime(df_5m: pd.DataFrame, adx_threshold: int = 25,
                     persistence: int = 2) -> pd.Series:
    """
    df_5m: 5-minute OHLCV DataFrame.
    Returns a Series of 'trending' / 'ranging', same index as df_5m.
    """
    adx_series = adx(df_5m, period=14)
    raw_regime = (adx_series > adx_threshold).map({True: "trending", False: "ranging"})

    # Persistence filter: only flip regime once it holds for `persistence` candles
    last_confirmed = None
    run_length = 0
    run_value = None

    result = []
    for value in raw_regime:
        if pd.isna(value):
            result.append(None)
            continue
        if value == run_value:
            run_length += 1
        else:
            run_value = value
            run_length = 1

        if run_length >= persistence:
            last_confirmed = value
        result.append(last_confirmed)

    return pd.Series(result, index=df_5m.index, name="regime")
