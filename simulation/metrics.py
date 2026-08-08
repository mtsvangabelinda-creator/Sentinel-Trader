import numpy as np
import pandas as pd


def sharpe_ratio(daily_returns: pd.Series, periods_per_year: int = 365) -> float:
    if daily_returns.std() == 0 or len(daily_returns) < 2:
        return 0.0
    return float(np.sqrt(periods_per_year) * daily_returns.mean() / daily_returns.std())


def max_drawdown(equity_curve: pd.Series) -> float:
    """Returns max drawdown as a positive fraction, e.g. 0.18 = 18%."""
    running_max = equity_curve.cummax()
    drawdown = (equity_curve - running_max) / running_max
    return float(abs(drawdown.min())) if len(drawdown) else 0.0


def profit_factor(trade_pnls: pd.Series) -> float:
    gains = trade_pnls[trade_pnls > 0].sum()
    losses = -trade_pnls[trade_pnls < 0].sum()
    if losses == 0:
        return float("inf") if gains > 0 else 0.0
    return float(gains / losses)


def win_rate(trade_pnls: pd.Series) -> float:
    if len(trade_pnls) == 0:
        return 0.0
    return float((trade_pnls > 0).sum() / len(trade_pnls))


def summarize(trades_df: pd.DataFrame, equity_curve: pd.Series) -> dict:
    """
    trades_df must have a 'pnl_usd' column (one row per closed trade) and,
    for Sharpe, a 'close_date' column to aggregate into daily returns.
    """
    if trades_df.empty:
        return {
            "num_trades": 0, "sharpe": 0.0, "max_drawdown": 0.0,
            "profit_factor": 0.0, "win_rate": 0.0,
        }

    daily_pnl = trades_df.groupby("close_date")["pnl_usd"].sum()
    starting_equity = equity_curve.iloc[0] if len(equity_curve) else 350.0
    daily_returns = daily_pnl / starting_equity

    return {
        "num_trades": len(trades_df),
        "sharpe": sharpe_ratio(daily_returns),
        "max_drawdown": max_drawdown(equity_curve),
        "profit_factor": profit_factor(trades_df["pnl_usd"]),
        "win_rate": win_rate(trades_df["pnl_usd"]),
    }
