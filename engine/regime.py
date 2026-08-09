import numpy as np
import pandas as pd
import logging
from .indicators import adx

logger = logging.getLogger(__name__)

class RegimeClassifier:
    """ADX-based regime classifier with persistence filter."""
    def __init__(self, config):
        self.period = config['regime']['adx_period']
        self.threshold = config['regime']['adx_threshold']
        self.persistence = config['regime']['persistence']
        self.history = []
        self.current_regime = 'ranging'
        self.adx_value = 0

    def update(self, candles_5m):
        """Update regime based on new 5m candles."""
        if len(candles_5m) < self.period + 1:
            return self.current_regime

        df = pd.DataFrame(candles_5m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        self.adx_value = adx(df, self.period)

        new_regime = 'trending' if self.adx_value > self.threshold else 'ranging'
        self.history.append(new_regime)

        if len(self.history) >= self.persistence:
            last_n = self.history[-self.persistence:]
            if all(r == new_regime for r in last_n):
                self.current_regime = new_regime

        if len(self.history) > 100:
            self.history = self.history[-100:]

        logger.debug(f"Regime: {self.current_regime}, ADX: {self.adx_value:.2f}")
        return self.current_regime
