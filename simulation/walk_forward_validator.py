import logging
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from .metrics import compute_metrics
from engine.kraken_data_fetcher import KrakenDataFetcher

logger = logging.getLogger(__name__)


class WalkForwardValidator:
    """Professional walk-forward validation with dynamic thresholds."""
    
    def __init__(self, config, alert):
        self.config = config
        self.alert = alert
        self.window_size_percent = 0.7  # 70% training
        self.oos_percent = 0.30  # 30% out-of-sample
        self.min_trades_required = 100
        self.oos_gate_multiplier = 0.7  # OOS must be >= 0.7 * IS Sharpe
    
    async def validate_with_walk_forward(self, all_trades, total_candles):
        """
        Run walk-forward validation.
        
        Splits data into multiple rolling windows:
        - Window 1: candles 0-70% (train), 70-100% (test)
        - Window 2: candles 10%-80% (train), 80-110% (test)
        - etc...
        
        Returns: (passed, metrics_dict)
        """
        
        logger.info("🔄 Starting Walk-Forward Validation...")
        await self.alert.send_message("🔄 Validating with Walk-Forward Analysis...\n(Testing across 70/30 rolling windows)")
        
        try:
            if not all_trades or len(all_trades) < self.min_trades_required:
                logger.warning(f"Insufficient trades: {len(all_trades)} (need ≥{self.min_trades_required})")
                return False, {
                    'error': f'Insufficient trades: {len(all_trades)} (need ≥{self.min_trades_required})',
                    'trades_count': len(all_trades),
                    'requirement': self.min_trades_required
                }
            
            # Calculate dynamic thresholds from data
            all_sharpes = []
            all_dd = []
            all_pf = []
            all_wr = []
            
            window_results = []
            num_windows = 5  # Test on 5 rolling windows
            
            # Calculate window size
            total_minutes = total_candles
            train_size = int(total_minutes * self.window_size_percent)
            test_size = int(total_minutes * self.oos_percent)
            step_size = int(total_minutes * 0.15)  # 15% overlap
            
            logger.info(f"Running {num_windows} rolling window tests...")
            logger.info(f"Train window: {train_size} candles, Test window: {test_size} candles")
            
            for window_idx in range(num_windows):
                start_idx = window_idx * step_size
                train_end = start_idx + train_size
                test_end = train_end + test_size
                
                if test_end > total_candles:
                    break
                
                # Split trades into IS (in-sample) and OOS (out-of-sample)
                is_trades = [t for t in all_trades if t.get('entry_time_idx', 0) < train_end]
                oos_trades = [t for t in all_trades if train_end <= t.get('entry_time_idx', 0) < test_end]
                
                if len(is_trades) < 10 or len(oos_trades) < 5:
                    continue
                
                # Calculate metrics
                is_metrics = compute_metrics(is_trades)
                oos_metrics = compute_metrics(oos_trades)
                
                # Check OOS gate: OOS Sharpe >= 0.7 * IS Sharpe
                oos_gate_threshold = is_metrics['sharpe'] * self.oos_gate_multiplier
                oos_passed = oos_metrics['sharpe'] >= oos_gate_threshold
                
                window_result = {
                    'window': window_idx + 1,
                    'is_trades': len(is_trades),
                    'oos_trades': len(oos_trades),
                    'is_sharpe': is_metrics['sharpe'],
                    'oos_sharpe': oos_metrics['sharpe'],
                    'oos_gate_threshold': oos_gate_threshold,
                    'oos_passed': oos_passed,
                    'is_dd': is_metrics['max_dd'],
                    'oos_dd': oos_metrics['max_dd'],
                    'is_pf': is_metrics['profit_factor'],
                    'oos_pf': oos_metrics['profit_factor']
                }
                
                window_results.append(window_result)
                
                if oos_passed:
                    all_sharpes.append(oos_metrics['sharpe'])
                    all_dd.append(oos_metrics['max_dd'])
                    all_pf.append(oos_metrics['profit_factor'])
                    all_wr.append(oos_metrics['win_rate'])
                
                logger.info(
                    f"Window {window_idx + 1}: "
                    f"IS Sharpe={is_metrics['sharpe']:.2f}, "
                    f"OOS Sharpe={oos_metrics['sharpe']:.2f}, "
                    f"Gate={'✅ PASS' if oos_passed else '❌ FAIL'}"
                )
            
            # Calculate dynamic thresholds from OOS results
            if not all_sharpes:
                logger.warning("No windows passed OOS gate")
                return False, {
                    'error': 'All windows failed OOS gate (OOS Sharpe < 0.7 × IS Sharpe)',
                    'window_results': window_results
                }
            
            # Dynamic threshold: mean - 1 std dev (conservative)
            dynamic_sharpe_threshold = np.mean(all_sharpes) - np.std(all_sharpes)
            dynamic_dd_threshold = np.mean(all_dd) + np.std(all_dd)  # Higher is worse
            
            # Overall validation passed if:
            passed_windows = sum(1 for w in window_results if w['oos_passed'])
            pass_rate = passed_windows / len(window_results) if window_results else 0
            
            overall_passed = (
                pass_rate >= 0.6 and  # At least 60% of windows pass
                len(all_sharpes) >= 3 and  # At least 3 windows passed
                np.std(all_sharpes) < 1.0  # OOS Sharpes are consistent (not too volatile)
            )
            
            summary = {
                'walk_forward_passed': overall_passed,
                'windows_tested': len(window_results),
                'windows_passed': passed_windows,
                'pass_rate': pass_rate,
                'oos_sharpe_mean': np.mean(all_sharpes) if all_sharpes else 0,
                'oos_sharpe_std': np.std(all_sharpes) if all_sharpes else 0,
                'oos_sharpe_min': np.min(all_sharpes) if all_sharpes else 0,
                'dynamic_sharpe_threshold': dynamic_sharpe_threshold,
                'total_trades': len(all_trades),
                'window_results': window_results
            }
            
            await self.alert.send_message(
                f"📊 <b>Walk-Forward Validation Results</b>\n\n"
                f"Windows Passed: {passed_windows}/{len(window_results)}\n"
                f"Pass Rate: {pass_rate*100:.1f}%\n"
                f"OOS Sharpe (mean±std): {np.mean(all_sharpes):.2f}±{np.std(all_sharpes):.2f}\n"
                f"Total Trades: {len(all_trades)}\n"
                f"Status: {'✅ PASSED' if overall_passed else '❌ FAILED'}"
            )
            
            logger.info(f"Walk-Forward Validation: {'✅ PASSED' if overall_passed else '❌ FAILED'}")
            return overall_passed, summary
        
        except Exception as e:
            logger.error(f"Walk-forward validation error: {e}", exc_info=True)
            await self.alert.send_error(f"Walk-forward validation error: {e}")
            return False, {'error': str(e)}
    
    def calculate_dynamic_thresholds(self, metrics_list):
        """Calculate data-driven thresholds instead of hardcoded values."""
        
        if not metrics_list:
            return {
                'sharpe_min': 0.5,
                'dd_max': 0.25,
                'pf_min': 1.2,
                'wr_min': 0.30
            }
        
        sharpes = [m['sharpe'] for m in metrics_list]
        dds = [m['max_dd'] for m in metrics_list]
        pfs = [m['profit_factor'] for m in metrics_list]
        wrs = [m['win_rate'] for m in metrics_list]
        
        # Dynamic thresholds: mean - 1 std dev (conservative, data-driven)
        return {
            'sharpe_min': max(0.3, np.mean(sharpes) - np.std(sharpes)),
            'dd_max': np.mean(dds) + np.std(dds),
            'pf_min': max(1.0, np.mean(pfs) - np.std(pfs)),
            'wr_min': max(0.20, np.mean(wrs) - np.std(wrs))
              }
