import logging
import asyncio
import pandas as pd
import optuna
from optuna.samplers import TPESampler
from simulation.run_backtest import _run_backtest_on_data
from simulation.metrics import compute_metrics

logger = logging.getLogger(__name__)

class AutoOptimizer:
    def __init__(self, config, db, alert):
        self.config = config
        self.db = db
        self.alert = alert

    async def run(self):
        """Run weekly optimization with Optuna."""
        try:
            df = pd.read_csv(self.config['historical_csv'])
        except:
            logger.error("Cannot load historical data")
            return None
        
        if len(df) < 500:
            logger.warning("Insufficient data for optimization")
            return None
        
        logger.info(f"Optimizing on {len(df)} candles")
        
        # Resample to 5m
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df_5m = df.set_index('timestamp').resample('5min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna().reset_index()
        
        # Use recent data for optimization (last 30 days worth)
        n_5m_bars = min(len(df_5m), 8640)  # ~30 days of 5m bars
        val_idx = max(0, len(df) - n_5m_bars * 5)
        df_opt = df.iloc[val_idx:].reset_index(drop=True)
        df_5m_opt = df_5m.iloc[-n_5m_bars:].reset_index(drop=True)
        
        logger.info(f"Opt set: {len(df_opt)} candles")
        
        def objective(trial):
            try:
                params = {
                    'regime': {
                        'adx_threshold': trial.suggest_int('adx_threshold', 20, 30)
                    },
                    'strategies': {
                        'trend_following': {
                            'breakout_period': trial.suggest_int('tf_breakout', 5, 20),
                            'atr_stop_mult': trial.suggest_float('tf_stop', 0.8, 1.5),
                            'atr_tp_mult': trial.suggest_float('tf_tp', 1.5, 3.0),
                            'trailing': False
                        },
                        'mean_reversion': {
                            'rsi_period': 7,
                            'rsi_oversold': trial.suggest_int('mr_oversold', 25, 35),
                            'rsi_overbought': trial.suggest_int('mr_overbought', 65, 75),
                            'bb_period': 20,
                            'bb_std': 2.0,
                            'atr_stop_mult': trial.suggest_float('mr_stop', 1.0, 2.0)
                        },
                        'momentum_burst': {
                            'adx_threshold': trial.suggest_int('mb_adx', 25, 40),
                            'consolidation_range': trial.suggest_float('mb_cons', 0.3, 0.7),
                            'atr_stop_mult': trial.suggest_float('mb_stop', 0.3, 0.7),
                            'atr_tp_mult': trial.suggest_float('mb_tp', 1.0, 2.0)
                        }
                    }
                }
                
                trades = asyncio.run(_run_backtest_on_data(df_opt, df_5m_opt, 
                                                           {**self.config, **params}))
                if len(trades) < 20:
                    return -1000.0
                
                metrics = compute_metrics(trades)
                score = metrics['sharpe'] * (1 - metrics['max_dd'])
                return score
            except:
                return -1000.0
        
        sampler = TPESampler(seed=42)
        study = optuna.create_study(sampler=sampler, direction='maximize')
        
        logger.info("Starting Optuna trials...")
        study.optimize(objective, n_trials=self.config['optimizer']['n_trials'], show_progress_bar=True)
        
        best = study.best_params
        candidate = {
            'regime': {'adx_threshold': best['adx_threshold']},
            'strategies': {
                'trend_following': {
                    'breakout_period': best['tf_breakout'],
                    'atr_stop_mult': best['tf_stop'],
                    'atr_tp_mult': best['tf_tp'],
                    'trailing': False
                },
                'mean_reversion': {
                    'rsi_oversold': best['mr_oversold'],
                    'rsi_overbought': best['mr_overbought'],
                    'atr_stop_mult': best['mr_stop']
                },
                'momentum_burst': {
                    'adx_threshold': best['mb_adx'],
                    'consolidation_range': best['mb_cons'],
                    'atr_stop_mult': best['mb_stop'],
                    'atr_tp_mult': best['mb_tp']
                }
            }
        }
        
        logger.info(f"Best candidate: {candidate}")
        return candidate
