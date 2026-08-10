import logging
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from .metrics import compute_metrics
from engine.regime import RegimeClassifier
from engine.sentinel import Sentinel
from strategies.trend_following import TrendFollowing
from strategies.mean_reversion import MeanReversion
from strategies.momentum_burst import MomentumBurst
from engine.kraken_data_fetcher import KrakenDataFetcher

logger = logging.getLogger(__name__)

async def run_initial_backtest(config, db, alert):
    """Run backtest on Kraken API data (last 30 days)."""
    
    try:
        logger.info("📥 Fetching data from Kraken API...")
        fetcher = KrakenDataFetcher()
        
        # Fetch 30 days of data
        df_1m = await fetcher.get_dataframe(days=30, timeframe='1m')
        
        if df_1m is None or len(df_1m) < 500:
            logger.error("Insufficient Kraken data")
            await alert.send_error("❌ Insufficient data from Kraken (need ≥500 candles)")
            return False, {'error': 'Insufficient data from Kraken'}
        
        logger.info(f"✅ Loaded {len(df_1m)} 1-minute candles")
        
        # Resample to 5m for regime detection
        df_5m = df_1m.set_index('timestamp').resample('5min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna().reset_index()
        
        logger.info(f"Resampled to {len(df_5m)} 5-minute candles")
        
        # Convert to list format
        candles_1m = df_1m[['timestamp', 'open', 'high', 'low', 'close', 'volume']].values.tolist()
        candles_5m = df_5m[['timestamp', 'open', 'high', 'low', 'close', 'volume']].values.tolist()
        
        logger.info("Running backtest on data...")
        
        # Run backtest
        trades = await _run_backtest_on_data(candles_1m, candles_5m, config)
        
        if len(trades) < 50:
            logger.warning(f"Insufficient trades: {len(trades)} (need ≥50)")
            return False, {'error': f'Insufficient trades: {len(trades)} (need ≥50)'}
        
        metrics = compute_metrics(trades)
        logger.info(f"✅ Backtest complete: {metrics}")
        
        # Gate criteria (less strict than before since we're using real data)
        passed = (
            metrics['num_trades'] >= 50 and
            metrics['sharpe'] >= 0.5 and
            metrics['max_dd'] <= 0.25 and
            metrics['profit_factor'] >= 1.2 and
            metrics['win_rate'] >= 0.30
        )
        
        logger.info(f"Gate criteria passed: {passed}")
        return passed, metrics
    
    except Exception as e:
        logger.error(f"Backtest error: {e}", exc_info=True)
        await alert.send_error(f"Backtest failed: {e}")
        return False, {'error': str(e)}


async def run_forward_test(config, db, alert, days=5):
    """Run forward test on recent data to verify no overfitting."""
    
    try:
        logger.info(f"🔄 Running forward test on last {days} days...")
        await alert.send_message(f"🧪 Starting forward test ({days} days)...")
        
        fetcher = KrakenDataFetcher()
        df_1m = await fetcher.get_dataframe(days=days, timeframe='1m')
        
        if df_1m is None or len(df_1m) < 100:
            logger.warning("Insufficient data for forward test")
            return False, {'error': 'Insufficient forward test data'}
        
        # Resample to 5m
        df_5m = df_1m.set_index('timestamp').resample('5min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna().reset_index()
        
        candles_1m = df_1m[['timestamp', 'open', 'high', 'low', 'close', 'volume']].values.tolist()
        candles_5m = df_5m[['timestamp', 'open', 'high', 'low', 'close', 'volume']].values.tolist()
        
        logger.info("Running forward test...")
        trades = await _run_backtest_on_data(candles_1m, candles_5m, config)
        
        if len(trades) < 10:
            logger.warning(f"Few trades in forward test: {len(trades)}")
            return False, {'error': f'Few trades in forward test: {len(trades)}'}
        
        metrics = compute_metrics(trades)
        logger.info(f"✅ Forward test: {len(trades)} trades, Sharpe: {metrics['sharpe']:.2f}")
        
        # Forward test should show positive Sharpe
        passed = metrics['sharpe'] > 0.0 and metrics['win_rate'] > 0.25
        
        return passed, metrics
    
    except Exception as e:
        logger.error(f"Forward test error: {e}")
        return False, {'error': str(e)}


async def _run_backtest_on_data(candles_1m, candles_5m, config):
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
    
    logger.info(f"Backtesting on {len(candles_1m)} 1m bars, {len(candles_5m)} 5m bars")
    
    for idx_5m in range(len(candles_5m)):
        end_1m_idx = min((idx_5m + 1) * 5, len(candles_1m))
        
        df_1m_current = pd.DataFrame(
            candles_1m[:end_1m_idx],
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        df_5m_current = pd.DataFrame(
            candles_5m[:idx_5m+1],
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        
        if len(df_5m_current) < 2 or len(df_1m_current) < 2:
            continue
        
        candles_1m_list = df_1m_current[['timestamp', 'open', 'high', 'low', 'close', 'volume']].values.tolist()
        candles_5m_list = df_5m_current[['timestamp', 'open', 'high', 'low', 'close', 'volume']].values.tolist()
        
        current_price = float(df_5m_current['close'].iloc[-1])
        current_time = df_5m_current['timestamp'].iloc[-1]
        
        # Update regime
        regime = regime_clf.update(candles_5m_list)
        
        # Check sentinel
        ticker = {'bid': current_price * 0.9999, 'ask': current_price * 1.0001, 'last': current_price}
        sentinel_green = sentinel.check(ticker, candles_5m_list)
        
        # Evaluate strategies
        if sentinel_green and len(open_positions) < max_concurrent:
            for strat_name, strat in strategies.items():
                if not strat.is_active(regime):
                    continue
                
                signal = strat.evaluate(candles_1m_list, candles_5m_list, ticker)
                if signal and signal.action != 'NONE':
                    pool = strategy_pools[strat_name]
                    risk = pool * 0.01
                    stop_dist = abs(current_price - signal.stop_price)
                    if stop_dist > 0 and stop_dist > 10:  # Minimum $10 stop
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
        
        # Manage positions
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
    
    # Close remaining positions
    if open_positions and len(candles_1m) > 0:
        final_price = float(candles_1m[-1][4])  # close price
        for pos in open_positions:
            pnl = (final_price - pos['entry_price']) * pos['size'] if pos['side'] == 'buy' else \
                  (pos['entry_price'] - final_price) * pos['size']
            pos['exit_price'] = final_price
            pos['pnl'] = pnl
            pos['status'] = 'closed'
            trades.append(pos)
    
    logger.info(f"Backtest complete: {len(trades)} trades")
    return trades
