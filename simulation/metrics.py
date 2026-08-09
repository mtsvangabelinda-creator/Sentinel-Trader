import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def compute_sharpe(returns, risk_free=0.0):
    """Compute annualized Sharpe ratio from list of returns."""
    if len(returns) == 0 or len(returns) < 2:
        return 0.0
    
    returns = np.array(returns)
    mean_ret = np.mean(returns)
    std_ret = np.std(returns)
    
    if std_ret == 0:
        return 0.0
    
    sharpe = (mean_ret - risk_free) / std_ret * np.sqrt(252)
    return sharpe

def max_drawdown(equity_curve):
    """Compute maximum drawdown from equity curve (list of values)."""
    if len(equity_curve) == 0:
        return 0.0
    
    equity = np.array(equity_curve)
    peak = equity[0]
    max_dd = 0.0
    
    for val in equity:
        if val > peak:
            peak = val
        dd = (peak - val) / peak if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd
    
    return max_dd

def profit_factor(trades):
    """Profit factor = gross profit / abs(gross loss)."""
    if len(trades) == 0:
        return 0.0
    
    gross_profit = sum(t['pnl'] for t in trades if t['pnl'] > 0)
    gross_loss = sum(abs(t['pnl']) for t in trades if t['pnl'] < 0)
    
    if gross_loss == 0:
        return float('inf') if gross_profit > 0 else 0.0
    
    return gross_profit / gross_loss

def win_rate(trades):
    """Win rate: percentage of profitable trades."""
    if len(trades) == 0:
        return 0.0
    
    wins = sum(1 for t in trades if t['pnl'] > 0)
    return wins / len(trades)

def compute_metrics(trades):
    """Compute all key metrics from trade list."""
    if len(trades) == 0:
        return {
            'num_trades': 0,
            'sharpe': 0.0,
            'max_dd': 0.0,
            'profit_factor': 0.0,
            'win_rate': 0.0,
            'total_pnl': 0.0
        }
    
    pnls = [t['pnl'] for t in trades]
    equity_curve = []
    cum = 0.0
    for pnl in pnls:
        cum += pnl
        equity_curve.append(cum)
    
    return {
        'num_trades': len(trades),
        'sharpe': compute_sharpe(pnls),
        'max_dd': max_drawdown(equity_curve),
        'profit_factor': profit_factor(trades),
        'win_rate': win_rate(trades),
        'total_pnl': sum(pnls)
    }
