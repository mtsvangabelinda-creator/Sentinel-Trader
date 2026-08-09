import logging
import asyncio
import pandas as pd
from simulation.run_backtest import _run_backtest_on_data
from simulation.metrics import compute_metrics

logger = logging.getLogger(__name__)

class ShadowRunner:
    """Run candidate config on recent live/simulated data."""
    def __init__(self, config, db):
        self.config = config
        self.db = db

    async def run(self, candidate):
        """Test candidate config on recent data."""
        try:
            df = pd.read_csv(self.config['historical_csv'])
        except:
            logger.error("Cannot load data for shadow test")
            return {'trades': [], 'sharpe': 0.0, 'num_trades': 0}
        
        # Use last 7 days of data
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df_7d = df.tail(7 * 24 * 60).reset_index(drop=True)
        
        df_5m = df_7d.set_index('timestamp').resample('5min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna().reset_index()
        
        logger.info(f"Shadow test on {len(df_7d)} 1m bars")
        
        # Merge candidate into config
        shadow_config = {**self.config, **candidate}
        
        # Run backtest
        trades = await _run_backtest_on_data(df_7d, df_5m, shadow_config)
        
        metrics = compute_metrics(trades)
        
        results = {
            'trades': trades,
            'sharpe': metrics['sharpe'],
            'max_dd': metrics['max_dd'],
            'profit_factor': metrics['profit_factor'],
            'win_rate': metrics['win_rate'],
            'num_trades': metrics['num_trades'],
            'start_date': df_7d['timestamp'].min(),
            'end_date': df_7d['timestamp'].max()
        }
        
        logger.info(f"Shadow results: {metrics}")
        return results
