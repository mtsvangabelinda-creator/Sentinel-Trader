from dataclasses import dataclass
from typing import Optional


@dataclass
class Signal:
    strategy: str          # 'trend_following' | 'mean_reversion' | 'momentum_burst'
    direction: str          # 'long' | 'short'
    entry_price: float
    stop_price: float
    take_profit_price: Optional[float]   # None allowed for MR (uses BB mid / RSI 50 exit)
    timestamp: object
    reason: str = ""
