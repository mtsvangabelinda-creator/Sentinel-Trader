"""
Export metrics for Prometheus in SentinelTrader
"""
from prometheus_client import Counter, Gauge, Histogram, start_http_server
from typing import Dict
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Define metrics
trades_total = Counter(
    'sentineltrader_trades_total',
    'Total trades executed',
    ['strategy', 'asset']
)

trades_pnl = Gauge(
    'sentineltrader_trades_pnl',
    'Trade P&L',
    ['strategy', 'asset']
)

account_equity = Gauge(
    'sentineltrader_account_equity',
    'Current account equity',
    ['strategy']
)

strategy_sharpe = Gauge(
    'sentineltrader_strategy_sharpe',
    'Strategy Sharpe ratio',
    ['strategy']
)

strategy_drawdown = Gauge(
    'sentineltrader_strategy_drawdown',
    'Strategy max drawdown',
    ['strategy']
)

position_size = Gauge(
    'sentineltrader_position_size',
    'Current position size',
    ['strategy', 'asset']
)

regime_state = Gauge(
    'sentineltrader_regime_state',
    'Current market regime',
    []
)

class MetricsExporter:
    """Export metrics to Prometheus"""
    
    @staticmethod
    def start_server(port: int = 8000):
        """Start Prometheus metrics server"""
        try:
            start_http_server(port)
            logger.info(f"Prometheus metrics server started on port {port}")
        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")
    
    @staticmethod
    def record_trade(strategy: str, asset: str, pnl: float):
        """Record trade execution"""
        trades_total.labels(strategy=strategy, asset=asset).inc()
        trades_pnl.labels(strategy=strategy, asset=asset).set(pnl)
        logger.debug(f"Trade recorded: {asset} P&L=${pnl:.2f}")
    
    @staticmethod
    def update_equity(strategy: str, equity: float):
        """Update account equity"""
        account_equity.labels(strategy=strategy).set(equity)
    
    @staticmethod
    def update_sharpe(strategy: str, sharpe: float):
        """Update Sharpe ratio"""
        strategy_sharpe.labels(strategy=strategy).set(sharpe)
    
    @staticmethod
    def update_drawdown(strategy: str, drawdown: float):
        """Update max drawdown"""
        strategy_drawdown.labels(strategy=strategy).set(drawdown)
    
    @staticmethod
    def update_regime(regime: int):
        """Update market regime"""
        regime_state.set(regime)
