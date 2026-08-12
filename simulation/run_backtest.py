import logging
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List

from engine.kraken_data_fetcher import KrakenDataFetcher
from simulation.walk_forward_validator import WalkForwardValidator
from simulation.metrics import compute_metrics
from strategies.base import Signal
from engine.regime_detector import RegimeClassifier
from engine.sentinel import Sentinel
from strategies.trend_following import TrendFollowing
from strategies.mean_reversion import MeanReversion
from strategies.momentum_burst import MomentumBurst
from strategies.volatility_breakout import VolatilityBreakout

logger = logging.getLogger(__name__)


class MultiTimeframeBacktester:
    """Runs backtest with 1m/5m/15m timeframe confirmation."""
    
    def __init__(self, config):
        self.config = config
        self.fetcher = KrakenDataFetcher()
        self.regime_classifier = RegimeClassifier()
        self.sentinel = Sentinel()
        
        # Initialize strategies
        self.strategies = [
            TrendFollowing(),
            MeanReversion(),
            MomentumBurst(),
            VolatilityBreakout()
        ]
    
    async def run_initial_backtest(self, config, db, alert):
        """Run backtest with professional walk-forward validation."""
        
        logger.info("🔄 STARTING MULTI-TIMEFRAME BACKTEST")
        
        try:
            # Fetch multi-timeframe data
            logger.info("📊 Fetching data from Kraken (1m, 5m, 15m)...")
            data_dict = await self.fetcher.get_dataframe(
                days=180,
                timeframes=[1, 5, 15]
            )
            
            if data_dict is None:
                logger.error("❌ Failed to fetch data")
                await alert.send_error("❌ Insufficient data from Kraken")
                return False, {'error': 'Insufficient data from Kraken'}
            
            df_1m = data_dict['1m']
            df_5m = data_dict['5m']
            df_15m = data_dict['15m']
            
            logger.info(f"✅ Loaded {len(df_1m)} 1m candles")
            logger.info(f"✅ Loaded {len(df_5m)} 5m candles")
            logger.info(f"✅ Loaded {len(df_15m)} 15m candles")
            
            # Align indices
            common_dates = df_1m.index.intersection(df_5m.index).intersection(df_15m.index)
            df_1m = df_1m.loc[common_dates]
            df_5m = df_5m.loc[common_dates]
            df_15m = df_15m.loc[common_dates]
            
            logger.info(f"✅ Aligned to {len(df_1m)} common candles")
            
            # Validate walk-forward
            logger.info("🔍 Validating with Walk-Forward Analysis...")
            wf_validator = WalkForwardValidator(
                train_ratio=0.7,
                num_windows=5
            )
            
            is_valid, metrics = wf_validator.validate(
                df_1m=df_1m,
                df_5m=df_5m,
                df_15m=df_15m,
                strategies=self.strategies,
                regime_classifier=self.regime_classifier,
                sentinel=self.sentinel
            )
            
            # Log results
            logger.info(f"\n📈 BACKTEST RESULTS:")
            logger.info(f"   Trades: {metrics.get('total_trades', 0)}")
            logger.info(f"   Sharpe: {metrics.get('sharpe_ratio', 0):.2f}")
            logger.info(f"   Win Rate: {metrics.get('win_rate', 0):.1%}")
            logger.info(f"   Max DD: {metrics.get('max_drawdown', 0):.2%}")
            
            if not is_valid:
                reason = metrics.get('fail_reason', 'Unknown')
                logger.error(f"❌ STAGE 0 FAILED: {reason}")
                await alert.send_error(f"❌ STAGE 0 FAILED\n\nReason: {reason}\n\nTrades: {metrics.get('total_trades', 0)}\nSharpe: {metrics.get('sharpe_ratio', 0):.2f}")
                return False, metrics
            
            logger.info("✅ STAGE 0 PASSED - Walk-Forward Validated")
            await alert.send_message("✅ STAGE 0 PASSED\n\nSystem ready for Stage 1 (Paper Trading)")
            
            return True, metrics
        
        except Exception as e:
            logger.error(f"❌ Backtest error: {e}", exc_info=True)
            await alert.send_error(f"❌ Backtest crashed: {str(e)}")
            return False, {'error': str(e)}


async def run_initial_backtest(config, db, alert):
    """Entry point for backtest."""
    backtester = MultiTimeframeBacktester(config)
    return await backtester.run_initial_backtest(config, db, alert)
