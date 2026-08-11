from dataclasses import dataclass


@dataclass
class Signal:
    """Trading signal from a strategy."""
    strategy: str
    action: str  # 'BUY', 'SELL', or 'NONE'
    entry_price: float
    stop_price: float
    take_profit: float
    confidence: float = 0.5
    reason: str = ""
