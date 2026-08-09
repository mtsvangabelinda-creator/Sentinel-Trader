import logging
from .indicators import atr

logger = logging.getLogger(__name__)

class Sentinel:
    """Safety gate: checks spread and volatility."""
    def __init__(self, config):
        self.max_spread_pct = config['sentinel']['max_spread_pct']
        self.range_multiplier = config['sentinel']['range_multiplier']

    def check(self, ticker, candles_5m):
        """Return True if market conditions are safe for entry."""
        if not ticker or 'bid' not in ticker or 'ask' not in ticker:
            return False

        bid = ticker['bid']
        ask = ticker['ask']
        
        if bid <= 0 or ask <= 0:
            return False

        spread_pct = (ask - bid) / bid * 100
        if spread_pct > self.max_spread_pct:
            logger.debug(f"Sentinel: Spread too wide {spread_pct:.4f}%")
            return False

        if len(candles_5m) < 15:
            return True

        try:
            atr_val = atr(candles_5m, period=14)
            if atr_val == 0:
                return True
            
            current_candle = candles_5m[-1]
            candle_range = current_candle[2] - current_candle[3]
            
            if candle_range > self.range_multiplier * atr_val:
                logger.debug(f"Sentinel: Candle range too wide {candle_range:.2f} vs {self.range_multiplier * atr_val:.2f}")
                return False
        except Exception as e:
            logger.debug(f"Sentinel check error: {e}")
            return True

        return True
