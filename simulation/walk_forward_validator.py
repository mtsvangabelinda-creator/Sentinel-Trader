import logging
import pandas as pd
import numpy as np
from typing import Tuple, Dict, List

from simulation.metrics import compute_metrics

logger = logging.getLogger(__name__)


class WalkForwardValidator:
    """Professional walk-forward validation across 3 timeframes."""
    
    def __init__(self, train_ratio: float = 0.7, num_windows: int = 5):
        self.train_ratio = train_ratio
        self.num_windows = num_windows
    
    def validate(self, df_1m, df_5m, df_15m, strategies, regime_classifier, sentinel) -> Tuple[bool, Dict]:
        """
        Run walk-forward validation.
        
        Returns:
            (is_valid, metrics_dict)
        """
        
        all_trades = []
        window_results = []
        
        # Split data into rolling windows
        total_len = len(df_1m)
        window_size = total_len // self.num_windows
        train_size = int(window_size * self.train_ratio)
        
        for window_idx in range(self.num_windows):
            start_idx = window_idx * window_size
            end_idx = start_idx + window_size
            
            train_end_idx = start_idx + train_size
            test_start_idx = train_end_idx
            test_end_idx = end_idx
            
            # Split data
            train_1m = df_1m.iloc[start_idx:train_end_idx]
            train_5m = df_5m.iloc[start_idx:train_end_idx]
            train_15m = df_15m.iloc[start_idx:train_end_idx]
            
            test_1m = df_1m.iloc[test_start_idx:test_end_idx]
            test_5m = df_5m.iloc[test_start_idx:test_end_idx]
            test_15m = df_15m.iloc[test_start_idx:test_end_idx]
            
            logger.info(f"\n🔄 Window {window_idx + 1}/{self.num_windows}")
            logger.info(f"   Train: {len(train_1m)} candles | Test: {len(test_1m)} candles")
            
            # Train: Fit regime classifier
            regime_classifier.fit(train_1m)
            
            # Test: Generate signals on out-of-sample data
            window_trades = self._generate_signals_oos(
                test_1m, test_5m, test_15m,
                strategies, regime_classifier, sentinel
            )
            
            all_trades.extend(window_trades)
            
            # Metrics for this window
            if window_trades:
                window_pnl = sum([t['pnl'] for t in window_trades])
                window_wr = sum([1 for t in window_trades if t['pnl'] > 0]) / len(window_trades)
                logger.info(f"   Trades: {len(window_trades)} | PnL: ${window_pnl:.2f} | WR: {window_wr:.1%}")
                window_results.append({
                    'window': window_idx,
                    'trades': len(window_trades),
                    'pnl': window_pnl,
                    'win_rate': window_wr
                })
            else:
                logger.warning(f"   ⚠️ No trades generated in this window")
        
        # Compute aggregate metrics
        metrics = self._compute_aggregate_metrics(all_trades, window_results)
        
        # Validation gates
        is_valid = self._check_validation_gates(metrics, all_trades)
        
        return is_valid, metrics
    
    def _generate_signals_oos(self, df_1m, df_5m, df_15m, strategies, regime_classifier, sentinel):
        """Generate signals on out-of-sample data with multi-timeframe confirmation."""
        
        trades = []
        position = None
        
        # Iterate through 1m candles
        for idx in range(100, len(df_1m)):  # Start at 100 to allow indicators to warm up
            time = df_1m.index[idx]
            price = df_1m['close'].iloc[idx]
            
            # Get current candles
            current_1m = df_1m.iloc[idx]
            
            # Find corresponding 5m and 15m candles (they might not be at exact same time)
            five_m_idx = self._find_closest_index(df_5m.index, time)
            fifteen_m_idx = self._find_closest_index(df_15m.index, time)
            
            if five_m_idx is None or fifteen_m_idx is None:
                continue
            
            current_5m = df_5m.iloc[five_m_idx]
            current_15m = df_15m.iloc[fifteen_m_idx]
            
            # Classify regime on 1m data
            regime = regime_classifier.classify(df_1m.iloc[:idx+1])
            
            # Get signals from all strategies
            best_signal = None
            best_confidence = 0
            
            for strategy in strategies:
                signal = strategy.generate_signal(
                    df_1m=df_1m.iloc[:idx+1],
                    df_5m=df_5m.iloc[:five_m_idx+1],
                    df_15m=df_15m.iloc[:fifteen_m_idx+1],
                    regime=regime
                )
                
                if signal and signal.is_valid() and signal.confidence > best_confidence:
                    best_signal = signal
                    best_confidence = signal.confidence
            
            # Execute if signal passes Sentinel
            if best_signal and position is None:
                if sentinel.should_trade(best_signal, regime):
                    # Simulate entry
                    entry_price = price
                    exit_price = self._simulate_exit(df_1m, idx, best_signal, entry_price)
                    
                    pnl = (exit_price - entry_price) if best_signal.action == 'BUY' else (entry_price - exit_price)
                    
                    trades.append({
                        'entry_time': time,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'pnl': pnl,
                        'strategy': best_signal.strategy_name,
                        'confidence': best_signal.confidence
                    })
                    
                    position = best_signal
        
        return trades
    
    def _find_closest_index(self, index_series, target_time):
        """Find index of closest timestamp in series."""
        try:
            if target_time in index_series:
                return index_series.get_loc(target_time)
            else:
                # Find closest
                pos = index_series.searchsorted(target_time)
                if pos == 0:
                    return 0
                elif pos == len(index_series):
                    return len(index_series) - 1
                else:
                    # Return closest
                    left = index_series[pos - 1]
                    right = index_series[pos]
                    if abs((target_time - left).total_seconds()) < abs((target_time - right).total_seconds()):
                        return pos - 1
                    else:
                        return pos
        except:
            return None
    
    def _simulate_exit(self, df, entry_idx, signal, entry_price, max_bars=100):
        """Simulate exit after entry (simple: exit after N bars or on opposite signal)."""
        
        for i in range(entry_idx + 1, min(entry_idx + max_bars, len(df))):
            current_price = df['close'].iloc[i]
            
            # Stop loss
            if signal.stop_loss:
                if signal.action == 'BUY' and current_price < signal.stop_loss:
                    return signal.stop_loss
                elif signal.action == 'SELL' and current_price > signal.stop_loss:
                    return signal.stop_loss
            
            # Take profit
            if signal.take_profit:
                if signal.action == 'BUY' and current_price > signal.take_profit:
                    return signal.take_profit
                elif signal.action == 'SELL' and current_price < signal.take_profit:
                    return signal.take_profit
        
        # Exit at end of window
        return df['close'].iloc[-1]
    
    def _compute_aggregate_metrics(self, trades, window_results):
        """Compute overall backtest metrics."""
        
        if not trades:
            return {
                'total_trades': 0,
                'sharpe_ratio': -999,
                'win_rate': 0,
                'max_drawdown': 0,
                'profit_factor': 0,
                'fail_reason': 'Insufficient trades: 0 (need ≥100)'
            }
        
        # Calculate PnL
        pnls = [t['pnl'] for t in trades]
        total_pnl = sum(pnls)
        wins = sum(1 for p in pnls if p > 0)
        win_rate = wins / len(trades)
        
        # Sharpe ratio
        returns = np.array(pnls)
        if len(returns) > 1 and returns.std() > 0:
            sharpe = (returns.mean() / returns.std()) * np.sqrt(252 * 1440)  # Annualized
        else:
            sharpe = -999
        
        # Max drawdown
        cumulative = np.cumsum(pnls)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / (running_max + 1e-8)
        max_dd = abs(drawdown.min())
        
        # Profit factor
        wins_sum = sum([p for p in pnls if p > 0])
        losses_sum = abs(sum([p for p in pnls if p < 0]))
        profit_factor = wins_sum / (losses_sum + 1e-8) if losses_sum > 0 else 0
        
        return {
            'total_trades': len(trades),
            'sharpe_ratio': sharpe,
            'win_rate': win_rate,
            'max_drawdown': max_dd,
            'profit_factor': profit_factor,
            'total_pnl': total_pnl,
            'window_results': window_results,
            'fail_reason': None
        }
    
    def _check_validation_gates(self, metrics, trades):
        """Check if backtest passes validation criteria."""
        
        # Gate 1: Minimum trades
        if metrics['total_trades'] < 100:
            metrics['fail_reason'] = f"Insufficient trades: {metrics['total_trades']} (need ≥100)"
            return False
        
        # Gate 2: Positive Sharpe (out-of-sample)
        if metrics['sharpe_ratio'] < 0:
            metrics['fail_reason'] = f"Negative Sharpe: {metrics['sharpe_ratio']:.2f} (need ≥0)"
            return False
        
        # Gate 3: Win rate > 45%
        if metrics['win_rate'] < 0.45:
            metrics['fail_reason'] = f"Low win rate: {metrics['win_rate']:.1%} (need ≥45%)"
            return False
        
        # Gate 4: Max drawdown < 20%
        if metrics['max_drawdown'] > 0.20:
            metrics['fail_reason'] = f"High drawdown: {metrics['max_drawdown']:.1%} (need <20%)"
            return False
        
        return True
