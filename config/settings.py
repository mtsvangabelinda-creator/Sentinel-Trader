import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

class Config(dict):
    def __init__(self, path):
        self.path = Path(path)
        super().__init__()
        self.load()

    def load(self):
        if self.path.exists():
            with open(self.path, 'r') as f:
                data = yaml.safe_load(f) or {}
                self.update(data)
        else:
            self.update(DEFAULT_CONFIG)
            self.save()

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, 'w') as f:
            yaml.dump(dict(self), f, default_flow_style=False, sort_keys=False)

DEFAULT_CONFIG = {
    'mode': 'backtest',
    'db_path': 'data/sentinel.db',
    'data_dir': 'data/',
    'historical_csv': 'data/btc_usd_1m.csv',
    'strategy_pools': {'trend': 150, 'meanrev': 150, 'momentum': 50},
    'max_concurrent_trades': 3,
    'daily_loss_limit': 10.0,
    'sentinel': {
        'max_spread_pct': 0.05,
        'range_multiplier': 3.0
    },
    'regime': {
        'adx_period': 14,
        'adx_threshold': 25,
        'persistence': 2
    },
    'strategies': {
        'trend_following': {
            'breakout_period': 10,
            'atr_stop_mult': 1.0,
            'atr_tp_mult': 2.0,
            'trailing': False
        },
        'mean_reversion': {
            'rsi_period': 7,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'bb_period': 20,
            'bb_std': 2.0,
            'atr_stop_mult': 1.5
        },
        'momentum_burst': {
            'adx_threshold': 30,
            'consolidation_range': 0.5,
            'atr_stop_mult': 0.5,
            'atr_tp_mult': 1.5
        }
    },
    'optimizer': {
        'n_trials': 200,
        'train_split': 0.7,
        'val_split': 0.15,
        'test_split': 0.15
    },
    'shadow': {
        'min_trades': 50,
        'max_days': 7
    },
    'promotion': {
        'prob_threshold': 0.9,
        'min_profit_factor': 1.3,
        'max_dd_ratio': 1.0
    },
    'rollback': {
        'monitor_trades': 20,
        'sharpe_threshold': 0.0,
        'max_loss_pct': 1.5
    },
    'initial_config_done': False
}

def load_config():
    return Config('config/btc_config.yaml')

def load_env():
    load_dotenv()
    return {
        'KRAKEN_API_KEY': os.getenv('KRAKEN_API_KEY', ''),
        'KRAKEN_SECRET': os.getenv('KRAKEN_SECRET', ''),
        'TELEGRAM_TOKEN': os.getenv('TELEGRAM_TOKEN', ''),
        'TELEGRAM_CHAT_ID': os.getenv('TELEGRAM_CHAT_ID', '')
    }
