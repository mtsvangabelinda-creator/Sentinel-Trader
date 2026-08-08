"""
Stage 0 - Initial Historical Backtest.

Loads a 1-min BTC/USD CSV, resamples to 5-min for regime/TF/Momentum signals,
runs all three strategies bar-by-bar with the shared RiskManager, and checks
the Stage 0 gate criteria from the plan:

  - Minimum 200 closed trades
  - Sharpe >= 1.0, Max DD <= 18%, Profit Factor >= 1.4, Win Rate >= 35%
  - No decay in the last 100 trades (checked separately, see check_no_decay)

Usage:
    python -m simulation.run_backtest --csv data/btcusd_1m.csv

CSV format expected: columns timestamp,open,high,low,close,volume
timestamp must be parseable by pandas (UTC).
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from config.settings import load_config
from engine.regime import classify_regime
from engine.sentinel import sentinel_mask
from engine.risk_manager import RiskManager
from strategies import trend_following, mean_reversion, momentum_burst
from simulation.metrics import summarize, max_drawdown


def load_1m_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["timestamp"])
    df = df.set_index("timestamp").sort_index()
    required = {"open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing columns: {missing}")
    return df


def resample_5m(df_1m: pd.DataFrame) -> pd.DataFrame:
    return df_1m.resample("5min").agg({
        "open": "first", "high": "max", "low": "min",
        "close": "last", "volume": "sum",
    }).dropna()


def run_backtest(df_1m: pd.DataFrame, cfg: dict) -> dict:
    df_5m = resample_5m(df_1m)

    regime = classify_regime(
        df_5m, cfg["regime"]["adx_threshold"], cfg["regime"]["persistence_candles"]
    )
    sentinel_5m = sentinel_mask(
        df_5m, cfg["sentinel"]["max_spread_pct"], cfg["sentinel"]["max_candle_range_atr_mult"]
    )
    sentinel_1m = sentinel_mask(
        df_1m, cfg["sentinel"]["max_spread_pct"], cfg["sentinel"]["max_candle_range_atr_mult"]
    )

    tf_signals = trend_following.generate_signals(df_5m, regime, cfg["trend_following"])
    mb_signals = momentum_burst.generate_signals(df_5m, cfg["momentum_burst"])
    mr_signals = mean_reversion.generate_signals(df_1m, regime, cfg["mean_reversion"])

    rm = RiskManager(
        pools=cfg["capital"]["pools"],
        risk_per_trade_pct=cfg["risk"]["risk_per_trade_pct"],
        max_concurrent_positions=cfg["risk"]["max_concurrent_positions"],
        daily_loss_limit_usd=cfg["risk"]["daily_loss_limit_usd"],
    )

    fee = cfg["fees"]["taker_pct"]
    slippage = cfg["fees"]["slippage_pct"]

    equity = cfg["capital"]["total"]
    equity_curve = []
    closed_trades = []
    current_day = None

    tf_signals_5m_idx = set(tf_signals.index[tf_signals["signal"]])
    mb_signals_5m_idx = set(mb_signals.index[mb_signals["signal"]])

    for ts, row in df_1m.iterrows():
        day = ts.date()
        if day != current_day:
            rm.new_utc_day()
            current_day = day

        # --- check exits for open positions first ---
        for strategy in list(rm.open_positions.keys()):
            pos = rm.open_positions[strategy]
            hit_stop = (row["low"] <= pos["stop_price"]) if pos["direction"] == "long" \
                else (row["high"] >= pos["stop_price"])
            hit_tp = pos["take_profit_price"] is not None and (
                (row["high"] >= pos["take_profit_price"]) if pos["direction"] == "long"
                else (row["low"] <= pos["take_profit_price"])
            )
            if hit_stop or hit_tp:
                exit_price = pos["stop_price"] if hit_stop else pos["take_profit_price"]
                exit_price *= (1 - slippage) if pos["direction"] == "long" else (1 + slippage)
                gross = (exit_price - pos["entry_price"]) * pos["size"] if pos["direction"] == "long" \
                    else (pos["entry_price"] - exit_price) * pos["size"]
                fees_paid = (pos["entry_price"] + exit_price) * pos["size"] * fee
                pnl = gross - fees_paid
                equity += pnl
                rm.register_close(strategy, pnl)
                closed_trades.append({
                    "strategy": strategy, "direction": pos["direction"],
                    "entry_price": pos["entry_price"], "exit_price": exit_price,
                    "size": pos["size"], "pnl_usd": pnl,
                    "close_date": ts.date(), "close_time": ts,
                })

        safe_to_enter = bool(sentinel_1m.get(ts, False))

        # --- Mean Reversion: evaluated every 1-min bar ---
        if safe_to_enter and ts in mr_signals.index and mr_signals.loc[ts, "signal"]:
            _try_enter(rm, "mean_reversion", mr_signals.loc[ts], row["close"], ts)

        # --- Trend Following & Momentum Burst: evaluated on 5-min boundaries ---
        if ts in tf_signals_5m_idx and safe_to_enter and bool(sentinel_5m.get(ts, False)):
            _try_enter(rm, "trend_following", tf_signals.loc[ts], row["close"], ts)
        if ts in mb_signals_5m_idx and safe_to_enter and bool(sentinel_5m.get(ts, False)):
            _try_enter(rm, "momentum_burst", mb_signals.loc[ts], row["close"], ts)

        equity_curve.append({"timestamp": ts, "equity": equity})

    trades_df = pd.DataFrame(closed_trades)
    equity_df = pd.DataFrame(equity_curve).set_index("timestamp")
    metrics = summarize(trades_df, equity_df["equity"])
    metrics["final_equity"] = equity
    return {"metrics": metrics, "trades": trades_df, "equity_curve": equity_df}


def _try_enter(rm: RiskManager, strategy: str, signal_row: pd.Series, close_price: float, ts) -> None:
    direction = signal_row["direction"]
    stop_price = signal_row["stop_price"]
    tp_price = signal_row.get("take_profit_price", None)
    if pd.isna(stop_price) or direction == "none":
        return

    size = rm.position_size(strategy, close_price, stop_price)
    if size <= 0:
        return

    rm.register_open(strategy, {
        "direction": direction, "entry_price": close_price,
        "stop_price": stop_price, "take_profit_price": tp_price,
        "size": size, "entry_time": ts,
    })


def check_gate_criteria(metrics: dict) -> dict:
    checks = {
        "min_trades_200": metrics["num_trades"] >= 200,
        "sharpe_ge_1.0": metrics["sharpe"] >= 1.0,
        "max_dd_le_18pct": metrics["max_drawdown"] <= 0.18,
        "profit_factor_ge_1.4": metrics["profit_factor"] >= 1.4,
        "win_rate_ge_35pct": metrics["win_rate"] >= 0.35,
    }
    checks["ALL_PASS"] = all(checks.values())
    return checks


def check_no_decay(trades_df: pd.DataFrame, starting_equity: float) -> bool:
    """Sharpe of the last 100 trades' daily P&L must be >= 0."""
    if len(trades_df) < 100:
        return False
    from simulation.metrics import sharpe_ratio
    last_100 = trades_df.tail(100)
    daily_pnl = last_100.groupby("close_date")["pnl_usd"].sum()
    daily_returns = daily_pnl / starting_equity
    return sharpe_ratio(daily_returns) >= 0.0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="Path to 1-min OHLCV CSV")
    parser.add_argument("--test-split", type=float, default=0.15,
                         help="Fraction of data reserved as out-of-sample test set")
    args = parser.parse_args()

    cfg = load_config()
    df_1m = load_1m_csv(Path(args.csv))

    split_idx = int(len(df_1m) * (1 - args.test_split))
    test_df = df_1m.iloc[split_idx:]

    print(f"Loaded {len(df_1m):,} 1-min candles. Running OUT-OF-SAMPLE test on last "
          f"{len(test_df):,} candles ({args.test_split:.0%}).")

    result = run_backtest(test_df, cfg)
    metrics = result["metrics"]
    gates = check_gate_criteria(metrics)
    no_decay = check_no_decay(result["trades"], cfg["capital"]["total"])

    print("\n--- Stage 0 Backtest Results (out-of-sample) ---")
    for k, v in metrics.items():
        print(f"  {k}: {v}")
    print("\n--- Gate Criteria ---")
    for k, v in gates.items():
        print(f"  {k}: {v}")
    print(f"  no_decay_last_100_trades: {no_decay}")

    passed = gates["ALL_PASS"] and no_decay
    if passed:
        Path("READY_FOR_PAPER").touch()
        print("\n✅ PASSED. Flag file READY_FOR_PAPER created.")
    else:
        print("\n❌ FAILED gate criteria. Review strategy logic/parameters before proceeding.")

    result["trades"].to_csv("backtest_trades.csv", index=False)
    result["equity_curve"].to_csv("backtest_equity_curve.csv")
    print("\nSaved backtest_trades.csv and backtest_equity_curve.csv")


if __name__ == "__main__":
    main()
