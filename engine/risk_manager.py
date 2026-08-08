"""
Hard-coded safety rules. These are never touched by the optimizer -- only
strategy parameters are tunable (see config/btc_config.yaml comments).
"""
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class RiskManager:
    pools: Dict[str, float]                 # e.g. {"trend_following": 150, ...}
    risk_per_trade_pct: float = 0.01
    max_concurrent_positions: int = 3
    daily_loss_limit_usd: float = 10.0

    open_positions: Dict[str, dict] = field(default_factory=dict)   # strategy -> position
    daily_realized_pnl: float = 0.0
    trading_blocked_today: bool = False

    def position_size(self, strategy: str, entry_price: float, stop_price: float) -> float:
        """Returns position size in BTC. 0 if trade should be rejected."""
        if self.trading_blocked_today:
            return 0.0
        if strategy in self.open_positions:
            return 0.0  # one position per strategy pool, no stacking
        if len(self.open_positions) >= self.max_concurrent_positions:
            return 0.0

        pool = self.pools.get(strategy, 0.0)
        risk_usd = pool * self.risk_per_trade_pct
        stop_distance = abs(entry_price - stop_price)
        if stop_distance <= 0:
            return 0.0

        size_btc = risk_usd / stop_distance
        # Never risk more notional than the pool itself
        max_notional_size = pool / entry_price
        return min(size_btc, max_notional_size)

    def register_open(self, strategy: str, position: dict) -> None:
        self.open_positions[strategy] = position

    def register_close(self, strategy: str, realized_pnl_usd: float) -> None:
        self.open_positions.pop(strategy, None)
        self.daily_realized_pnl += realized_pnl_usd
        if self.daily_realized_pnl <= -abs(self.daily_loss_limit_usd):
            self.trading_blocked_today = True

    def new_utc_day(self) -> None:
        self.daily_realized_pnl = 0.0
        self.trading_blocked_today = False
