import logging
import os
from dotenv import load_dotenv
import yaml

logger = logging.getLogger(__name__)
load_dotenv()


class Config(dict):
    """Configuration dictionary with load/save capabilities."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config_file = 'config/btc_config.yaml'
    
    def save(self):
        """Save config to YAML file."""
        try:
            with open(self.config_file, 'w') as f:
                yaml.dump(dict(self), f)
            logger.info(f"✅ Config saved to {self.config_file}")
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    def load(self):
        """Load config from YAML file."""
        try:
            with open(self.config_file, 'r') as f:
                data = yaml.safe_load(f)
                if data:
                    self.update(data)
            logger.info(f"✅ Config loaded from {self.config_file}")
        except Exception as e:
            logger.error(f"Error loading config: {e}")


# Default configuration
DEFAULT_CONFIG = {
    'mode': 'backtest',
    'initial_config_done': False,
    
    # Strategy pools ($)
    'strategy_pools': {
        'trend': 100,
        'meanrev': 100,
        'momentum': 75,
        'volatility': 75
    },
    
    # Risk management
    'max_concurrent_trades': 3,
    'risk_per_trade': 0.01,  # 1% of capital
    'daily_loss_limit': 10.00,
    
    # Backtest parameters
    'backtest_window_days': 60,
    'min_trades_required': 100,
    'sharpe_threshold': 0.5,
    'max_dd_threshold': 0.25,
    'profit_factor_threshold': 1.2,
    'win_rate_threshold': 0.30,
    
    # Walk-forward validation (PROFESSIONAL STANDARD)
    'walk_forward_enabled': True,
    'walk_forward_train_ratio': 0.70,
    'walk_forward_test_ratio': 0.30,
    'walk_forward_num_windows': 5,
    'walk_forward_oos_gate_multiplier': 0.7,  # OOS must be >= 0.7 * IS Sharpe
    
    # Optimizer
    'optimizer_enabled': True,
    'optimizer_trials': 200,
    'optimizer_timeout_seconds': 300,
    
    # Regime detection (PROFESSIONAL STANDARD)
    'regime_detector_enabled': True,
    'regime_lookback_window': 100,
    'regime_ks_test_threshold': 0.05,  # p-value threshold
    
    # Shadow runner (Stage 2 validator)
    'shadow_runner_enabled': True,
    'shadow_runner_days': 7,
    
    # Promotion criteria (Stage 1 → Stage 2)
    'promotion_sharpe_min': 0.8,
    'promotion_dd_max': 0.15,
    'promotion_pf_min': 1.3,
    'promotion_wr_min': 0.35,
    'promotion_min_trades': 50,
    
    # Rollback triggers (Live safety)
    'rollback_sharpe_min': 0.0,
    'rollback_loss_percent_max': 1.5,
    'rollback_trade_lookback': 20,
    
    # Logging
    'log_level': 'INFO',
    'log_file': 'logs/sentineltrader.log',
    'sqlite_db': 'data/sentinel.db'
}


def load_env():
    """Load environment variables from .env file."""
    return {
        'KRAKEN_API_KEY': os.getenv('KRAKEN_API_KEY'),
        'KRAKEN_SECRET': os.getenv('KRAKEN_SECRET'),
        'TELEGRAM_TOKEN': os.getenv('TELEGRAM_TOKEN'),
        'TELEGRAM_CHAT_ID': os.getenv('TELEGRAM_CHAT_ID')
    }


def load_config():
    """Load configuration from file or use defaults."""
    config = Config(DEFAULT_CONFIG)
    
    # Try to load from file
    config.load()
    
    return config
