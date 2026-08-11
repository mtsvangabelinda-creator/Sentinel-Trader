import logging
import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


class RegimeDetector:
    """Detect market regime shifts using statistical tests."""
    
    def __init__(self, lookback_window=100):
        self.lookback_window = lookback_window
        self.training_returns = None
        self.training_std = None
        self.alert = None
    
    def set_alert_handler(self, alert):
        """Set Telegram alert handler."""
        self.alert = alert
    
    async def train_on_backtest(self, candles):
        """Learn the training distribution from backtest data."""
        if len(candles) < self.lookback_window:
            logger.warning("Not enough data to train regime detector")
            return
        
        # Calculate returns
        closes = np.array([c[4] for c in candles])
        returns = np.diff(closes) / closes[:-1]
        
        self.training_returns = returns[-self.lookback_window:]
        self.training_std = np.std(self.training_returns)
        self.training_mean = np.mean(self.training_returns)
        
        logger.info(f"Regime detector trained: mean={self.training_mean:.4f}, std={self.training_std:.4f}")
    
    async def detect_shift(self, live_candles, alert):
        """
        Detect regime shift using KS-test.
        
        Returns: (regime_shifted: bool, p_value: float)
        """
        
        if self.training_returns is None or len(live_candles) < self.lookback_window:
            return False, 1.0
        
        # Calculate returns from live data
        closes = np.array([c[4] for c in live_candles])
        live_returns = np.diff(closes) / closes[:-1]
        live_returns = live_returns[-self.lookback_window:]
        
        # KS-test: compare training distribution to live distribution
        ks_stat, p_value = stats.ks_2samp(self.training_returns, live_returns)
        
        # Regime shift if p < 0.05 (95% confidence)
        regime_shifted = p_value < 0.05
        
        if regime_shifted:
            logger.warning(f"⚠️ REGIME SHIFT DETECTED! p-value={p_value:.4f}, KS-stat={ks_stat:.4f}")
            
            # Calculate what changed
            live_std = np.std(live_returns)
            live_mean = np.mean(live_returns)
            
            shift_description = f"Volatility: {self.training_std:.4f} → {live_std:.4f}"
            
            if alert:
                await alert.send_message(
                    f"⚠️ <b>REGIME SHIFT DETECTED</b>\n\n"
                    f"KS-test p-value: {p_value:.4f} (threshold: 0.05)\n"
                    f"Volatility change: {self.training_std:.4f} → {live_std:.4f}\n"
                    f"Return mean: {self.training_mean:.4f} → {live_mean:.4f}\n\n"
                    f"System will halt live trading and restart backtest with new data."
                )
        
        return regime_shifted, p_value
    
    def get_volatility_multiplier(self, live_candles):
        """
        Calculate dynamic position sizing multiplier based on volatility.
        
        If volatility increased 2x, reduce position size by 0.5x
        """
        
        if self.training_std == 0 or len(live_candles) < self.lookback_window:
            return 1.0
        
        closes = np.array([c[4] for c in live_candles])
        live_returns = np.diff(closes) / closes[:-1]
        live_std = np.std(live_returns[-self.lookback_window:])
        
        # Multiplier = training_vol / current_vol
        # If vol doubled, multiplier = 0.5 (reduce position size)
        multiplier = self.training_std / live_std if live_std > 0 else 1.0
        
        # Cap between 0.5 and 2.0 (don't be extreme)
        multiplier = np.clip(multiplier, 0.5, 2.0)
        
        return multiplier
