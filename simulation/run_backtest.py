import logging
import pandas as pd
import numpy as np
from datetime import datetime
from .metrics import compute_metrics
from engine.regime import RegimeClassifier
from engine.sentinel import Sentinel
from strategies.trend_following import TrendFollowing
from strategies.mean_reversion import MeanReversion
from strategies.momentum_burst import MomentumBurst
from engine.indicators import atr

logger = logging.getLogger(__name__)

async def run_initial_backtest(config, db, alert):
    """Run backtest on historical data and check gate criteria."""
    try:
        # Load historical CSV
        df = pd.read_csv(config['historical_csv'], parse_dates=['timestamp'])
    except FileNotFoundError:
        logger.error("Historical CSV not found")
        return False, {'error': 'CSV not found'}
    
    if len(df) < 500:
        return False, {'error': 'Insufficient historical data'}
    
    logger.info(f"Loaded {len(df)} 1m candles")
    
    # Resample to 5m for regime detection
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df_5m = df.set_index('timestamp').resample('5min').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna().reset_index()
    
    # Split data: train/val/test
    n = len(df)
    train_end = int(n * config['optimizer']['train_split'])
    val_end = train_end + int(n * config['optimizer']['val_split'])
    
    df_test = df.iloc[val_end:].reset_index(drop=True)
    df_5m_test = df_5m.iloc[val_end // 5:].reset_index(drop=True)
    
    logger.info(f"Test set: {len(df_test)} 1m candles, {len(df_5m_test)} 5m candles")
    
    # Run backtest on test set
    trades = await _run_backtest_on_data(df_test, df_5m_test, config)
    
    if len(trades) == 0:
        return False, {'error': 'No trades generated'}
    
    metrics = compute_metrics(trades)
    logger.info(f"Backtest metrics: {metrics}")
    
    # Check gate criteria
    passed = (
        metrics['num_trades'] >= 200 and
        metrics['sharpe'] >= 1.0 and
        metrics['max_dd'] <= 0.18 and
        metrics['profit_factor'] >= 1.4 and
        metrics['win_rate'] >= 0.35
    )
    
    logger.info(f"Gate criteria passed: {passed}")
    return passed, metrics

async def _run_backtest_on_data(df_1m, df_5m, config):
    """Simulate trades on historical data."""
    trades = []
    open_positions = []
    
    regime_clf = RegimeClassifier(config)
    sentinel = Sentinel(config)
    
    strategies = {
        'trend': TrendFollowing(config),
        'meanrev': MeanReversion(config),
        'momentum': MomentumBurst(config)
    }
    
    strategy_pools = config['strategy_pools']
    max_concurrent = config['max_concurrent_trades']
    
    # Main backtest loop
    for idx_5m in range(len(df_5m)):
        # Get candles up to current 5m bar
        end_1m_idx = (idx_5m + 1) * 5
        if end_1m_idx > len(df_1m):
            end_1m_idx = len(df_1m)
        
        df_1m_current = df_1m.iloc[:end_1m_idx]
        df_5m_current = df_5m.iloc[:idx_5m+1]
        
        candles_1m = df_1m_current[['timestamp','open','high','low','close','volume']].values.tolist()
        candles_5m = df_5m_current[['timestamp','open','high','low','close','volume']].values.tolist()
        
        if len(candles_5m) < 2 or len(candles_1m) < 2:
            continue
        
        # Current price
        current_price = df_5m_current['close'].iloc[-1]
        current_time = df_5m_current['timestamp'].iloc[-1]
        
        # Update regime
        regime = regime_clf.update(candles_5m)
        
        # Check sentinel
        ticker = {'bid': current_price * 0.999, 'ask': current_price * 1.001, 'last': current_price}
        sentinel_green = sentinel.check(ticker, candles_5m)
        
        # Evaluate strategies
        if sentinel_green and len(open_positions) < max_concurrent:
            for strat_name, strat in strategies.items():
                if not strat.is_active(regime):
                    continue
                
                signal = strat.evaluate(candles_1m, candles_5m, ticker)
                if signal and signal.action != 'NONE':
                    # Calculate position size (1% risk)
                    pool = strategy_pools[strat_name]
                    risk = pool * 0.01
                    stop_dist = abs(current_price - signal.stop_price)
                    if stop_dist > 0:
                        size = risk / stop_dist
                        if size > 0.0001:
                            trade = {
                                'id': f"{idx_5m}_{strat_name}",
                                'strategy': strat_name,
                                'side': signal.action.lower(),
                                'entry_price': current_price,
                                'entry_time': current_time,
                                'size': size,
                                'stop_price': signal.stop_price,
                                'take_profit': signal.take_profit,
                                'exit_price': None,
                                'exit_time': None,
                                'pnl': None,
                                'status': 'open'
                            }
                            open_positions.append(trade)
        
        # Manage open positions
        for pos in list(open_positions):
            exit_reason = None
            
            if pos['side'] == 'buy':
                if current_price >= pos['take_profit']:
                    exit_reason = 'tp'
                elif current_price <= pos['stop_price']:
                    exit_reason = 'sl'
            else:
                if current_price <= pos['take_profit']:
                    exit_reason = 'tp'
                elif current_price >= pos['stop_price']:
                    exit_reason = 'sl'
            
            if exit_reason:
                pnl = (current_price - pos['entry_price']) * pos['size'] if pos['side'] == 'buy' else \
                      (pos['entry_price'] - current_price) * pos['size']
                
                pos['exit_price'] = current_price
                pos['exit_time'] = current_time
                pos['pnl'] = pnl
                pos['status'] = 'closed'
                
                trades.append(pos)
                open_positions.remove(pos)
    
    # Close any remaining positions
    if open_positions:
        final_price = df_1m.iloc[-1]['close']
        for pos in open_positions:
            pnl = (final_price - pos['entry_price']) * pos['size'] if pos['side'] == 'buy' else \
                  (pos['entry_price'] - final_price) * pos['size']
            pos['exit_price'] = final_price
            pos['pnl'] = pnl
            pos['status'] = 'closed'
            trades.append(pos)
    
    return trades
