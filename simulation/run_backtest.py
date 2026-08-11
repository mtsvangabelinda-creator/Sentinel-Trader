import logging
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from .metrics import compute_metrics
from .walk_forward_validator import WalkForwardValidator
from strategies.base import Signal
from engine.regime import RegimeClassifier
from engine.sentinel import Sentinel
from strategies.trend_following import TrendFollowing
from strategies.mean_reversion import MeanReversion
from strategies.momentum_burst import MomentumBurst
from strategies.volatility_breakout import VolatilityBreakout
from engine.kraken_data_fetcher import KrakenDataFetcher

logger = logging.getLogger(__name__)


async def run_initial_backtest(config, db, alert):
    """Run backtest with professional walk-forward validation."""
    
    try:
        logger.info("📥 Fetching data from Kraken API...")
        fetcher = KrakenDataFetcher()
        
        # Fetch 60 days of data
        df_1m = await fetcher.get_dataframe(days=60, timeframe='1m')
        
        if df_1m is None or len(df_1m) < 500:
            logger.error(f"Insufficient Kraken data: got {len(df_1m) if df_1m is not None else 0}")
            await alert.send_error(f"❌ Insufficient data from Kraken (got {len(df_1m) if df_1m is not None else 0}, need ≥500)")
            return False, {'error': 'Insufficient data from Kraken'}
        
        logger.info(f"✅ Loaded {len(df_1m)} 1-minute candles")
        
        # Resample to 5m
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
        
        logger.info("Running backtest simulation with 4 strategies...")
        
        # Run backtest
        trades = await _run_backtest_on_data(candles_1m, candles_5m, config)
        
        # Calculate metrics on full dataset
        full_metrics = compute_metrics(trades)
        logger.info(f"Full backtest: {len(trades)} trades, Sharpe: {full_metrics['sharpe']:.2f}")
        
        # NOW run walk-forward validation (professional gate)
        validator = WalkForwardValidator(config, alert)
        wf_passed, wf_results = await validator.validate_with_walk_forward(trades, len(candles_1m))
        
        if not wf_passed:
            logger.warning("Walk-Forward Validation FAILED")
            await alert.send_message(
                f"❌ <b>STAGE 0 FAILED - Walk-Forward Validation</b>\n\n"
                f"Full backtest metrics:\n"
                f"Trades: {len(trades)}\n"
                f"Sharpe: {full_metrics['sharpe']:.2f}\n\n"
                f"Issue: {wf_results.get('error', 'Unknown')}"
            )
            return False, wf_results
        
        logger.info("✅ Walk-Forward Validation PASSED")
        
        await alert.send_message(
            f"✅ <b>BACKTEST PASSED (Walk-Forward Validated)</b>\n\n"
            f"📊 Full Backtest:\n"
            f"Trades: {len(trades)}\n"
            f"Sharpe: {full_metrics['sharpe']:.2f}\n"
            f"Max DD: {full_metrics['max_dd']*100:.1f}%\n"
            f"Profit Factor: {full_metrics['profit_factor']:.2f}\n"
            f"Win Rate: {full_metrics['win_rate']*100:.1f}%\n\n"
            f"🔬 Walk-Forward:\n"
            f"Windows Passed: {wf_results['windows_passed']}/{wf_results['windows_tested']}\n"
            f"OOS Sharpe: {wf_results['oos_sharpe_mean']:.2f}±{wf_results['oos_sharpe_std']:.2f}\n\n"
            f"🧪 Running forward test..."
        )
        
        # Run forward test
        fw_passed, fw_metrics = await run_forward_test(config, db, alert, days=5)
        
        if not fw_passed or fw_metrics.get('sharpe', 0) < 0.0:
            logger.warning("Forward test underperformed")
            await alert.send_message(
                f"⚠️ <b>FORWARD TEST UNDERPERFORMED</b>\n\n"
                f"Backtest Sharpe: {full_metrics['sharpe']:.2f}\n"
                f"Forward Sharpe: {fw_metrics.get('sharpe', 'N/A')}\n\n"
                f"Adjusting parameters and retrying..."
            )
            return False, fw_metrics
        
        logger.info("✅ Forward test PASSED")
        
        # Update config
        config['initial_config_done'] = True
        config['mode'] = 'paper'
        config.save()
        
        await alert.send_message(
            f"🟢 <b>STAGE 0 & FORWARD TEST PASSED</b>\n\n"
            f"📈 Backtest Sharpe: {full_metrics['sharpe']:.2f}\n"
            f"🧪 Forward Test Sharpe: {fw_metrics['sharpe']:.2f}\n"
            f"✅ Walk-Forward Validated (Professional Standard)\n\n"
            f"Transitioning to Stage 1 (Paper Trading)..."
        )
        
        return True, {
            'full_metrics': full_metrics,
            'walk_forward': wf_results,
            'forward_test': fw_metrics
        }
    
    except Exception as e:
        logger.error(f"Backtest error: {e}", exc_info=True)
        await alert.send_error(f"Backtest failed: {e}")
        return False, {'error': str(e)}


async def run_forward_test(config, db, alert, days=5):
    """Run forward test on recent data."""
    
    try:
        logger.info(f"Running forward test on last {days} days...")
        
        fetcher = KrakenDataFetcher()
        df_1m = await fetcher.get_dataframe(days=days, timeframe='1m')
        
        if df_1m is None or len(df_1m) < 100:
            return False, {'error': 'Insufficient forward test data'}
        
        df_5m = df_1m.set_index('timestamp').resample('5min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna().reset_index()
        
        candles_1m = df_1m[['timestamp', 'open', 'high', 'low', 'close', 'volume']].values.tolist()
        candles_5m = df_5m[['timestamp', 'open', 'high', 'low', 'close', 'volume']].values.tolist()
        
        trades = await _run_backtest_on_data(candles_1m, candles_5m, config)
        metrics = compute_metrics(trades)
        
        logger.info(f"Forward test: {len(trades)} trades, Sharpe: {metrics['sharpe']:.2f}")
        return True, metrics
    
    except Exception as e:
        logger.error(f"Forward test error: {e}")
        return False, {'error': str(e)}


async def _run_backtest_on_data(candles_1m, candles_5m, config):
    """Simulate trades on historical data with 4 strategies."""
    trades = []
    open_positions = []
    
    regime_clf = RegimeClassifier(config)
    sentinel = Sentinel(config)
    
    # 4 strategies
    strategies = {
        'trend': TrendFollowing(config),
        'meanrev': MeanReversion(config),
        'momentum': MomentumBurst(config),
        'volatility': VolatilityBreakout(config)
    }
    
    strategy_pools = config['strategy_pools']
    max_concurrent = config['max_concurrent_trades']
    
    logger.info(f"Backtesting on {len(candles_1m)} 1m bars, {len(candles_5m)} 5m bars with 4 strategies")
    
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
        entry_time_idx = end_1m_idx
        
        regime = regime_clf.update(candles_5m_list)
        ticker = {'bid': current_price * 0.9999, 'ask': current_price * 1.0001, 'last': current_price}
        sentinel_green = sentinel.check(ticker, candles_5m_list)
        
        if sentinel_green and len(open_positions) < max_concurrent:
            for strat_name, strat in strategies.items():
                if not strat.is_active(regime):
                    continue
                
                signal_dict = strat.evaluate(candles_1m_list, candles_5m_list, ticker)
                if signal_dict is None:
                    continue
                
                # Convert dict to Signal object
                signal = Signal(
                    strategy=signal_dict['strategy'],
                    action=signal_dict['action'],
                    entry_price=signal_dict['entry_price'],
                    stop_price=signal_dict['stop_price'],
                    take_profit=signal_dict['take_profit'],
                    confidence=signal_dict.get('confidence', 0.5),
                    reason=signal_dict.get('reason', '')
                )
                
                if signal and signal.action != 'NONE':
                    pool = strategy_pools.get(strat_name, 50)
                    risk = pool * 0.01
                    stop_dist = abs(current_price - signal.stop_price)
                    if stop_dist > 0 and stop_dist > 10:
                        size = risk / stop_dist
                        if size > 0.0001:
                            trade = {
                                'id': f"{idx_5m}_{strat_name}",
                                'strategy': strat_name,
                                'side': signal.action.lower(),
                                'entry_price': current_price,
                                'entry_time': current_time,
                                'entry_time_idx': entry_time_idx,
                                'size': size,
                                'stop_price': signal.stop_price,
                                'take_profit': signal.take_profit,
                                'exit_price': None,
                                'exit_time': None,
                                'pnl': None,
                                'status': 'open'
                            }
                            open_positions.append(trade)
        
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
    
    if open_positions and len(candles_1m) > 0:
        final_price = float(candles_1m[-1][4])
        for pos in open_positions:
            pnl = (final_price - pos['entry_price']) * pos['size'] if pos['side'] == 'buy' else \
                  (pos['entry_price'] - final_price) * pos['size']
            pos['exit_price'] = final_price
            pos['pnl'] = pnl
            pos['status'] = 'closed'
            trades.append(pos)
    
    logger.info(f"Backtest complete: {len(trades)} trades from 4 strategies")
    return trades
