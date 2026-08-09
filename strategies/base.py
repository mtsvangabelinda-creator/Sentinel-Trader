from dataclasses import dataclass

@dataclass
class Signal:
    strategy: str
    action: str  # 'BUY', 'SELL', 'NONE'
    entry_price: float
    stop_price: float
    take_profit: float
    confidence: float = 1.0
