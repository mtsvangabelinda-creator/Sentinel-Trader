import logging
import pandas as pd

logger = logging.getLogger(__name__)


class Sentinel:
    """
    Multi-timeframe gatekeeper that filters signals based on market conditions.
    Only allows trades when market conditions align with signal direction.
    """
    
    def __init__(self):
        self.name = "Sentinel"
        self.enabled = True
    
    def should_trade(self, signal, regime: str) -> bool:
        """
        Determine if a signal should be executed based on market conditions.
        
        Args:
            signal: Signal object with multi-timeframe data
            regime: Current market regime classification
        
        Returns:
            True if signal passes all gates, False otherwise
        """
        
        if not self.enabled:
            return True
        
        # Gate 1: Signal must be valid
        if not signal.is_valid():
            logger.debug(f"❌ Sentinel: Invalid signal from {signal.strategy_name}")
            return False
        
        # Gate 2: Timeframe alignment
        if not signal.tf_1m_signal or not signal.tf_5m_confirmed:
            logger.debug(f"❌ Sentinel: Timeframe alignment failed for {signal.strategy_name}")
            return False
        
        # Gate 3: 15m bias must align
        if signal.action == 'BUY' and signal.tf_15m_bias != 'UP':
            logger.debug(f"❌ Sentinel: Buy signal but 15m bias={signal.tf_15m_bias}")
            return False
        
        if signal.action == 'SELL' and signal.tf_15m_bias != 'DOWN':
            logger.debug(f"❌ Sentinel: Sell signal but 15m bias={signal.tf_15m_bias}")
            return False
        
        # Gate 4: Regime compatibility
        if not self._is_regime_compatible(signal, regime):
            logger.debug(f"❌ Sentinel: Regime {regime} incompatible with {signal.strategy_name}")
            return False
        
        # Gate 5: Risk/Reward acceptable
        if signal.risk_reward_ratio and signal.risk_reward_ratio < 1.0:
            logger.debug(f"❌ Sentinel: Poor risk/reward ratio {signal.risk_reward_ratio:.2f}")
            return False
        
        # Gate 6: Confidence threshold
        if signal.confidence < 0.6:
            logger.debug(f"❌ Sentinel: Low confidence {signal.confidence:.2f}")
            return False
        
        logger.info(f"✅ Sentinel PASSED: {signal.strategy_name} ({signal.action}) | Confidence={signal.confidence:.2f}")
        return True
    
    def _is_regime_compatible(self, signal, regime: str) -> bool:
        """
        Check if signal is compatible with current market regime.
        
        Regime types: 'TRENDING_UP', 'TRENDING_DOWN', 'RANGING', 'VOLATILE'
        """
        
        strategy = signal.strategy_name
        action = signal.action
        
        # Trend Following: Works in trending regimes
        if strategy == "TrendFollowing":
            if regime == "TRENDING_UP" and action == "BUY":
                return True
            if regime == "TRENDING_DOWN" and action == "SELL":
                return True
            if regime == "RANGING" or regime == "VOLATILE":
                return False  # Trend followers lose in choppy markets
        
        # Mean Reversion: Works in ranging/sideways regimes
        if strategy == "MeanReversion":
            if regime == "RANGING":
                return True  # Mean reversion ideal in ranges
            if regime == "TRENDING_UP" or regime == "TRENDING_DOWN":
                return False  # Mean reversion fails in trends
            if regime == "VOLATILE":
                return False  # Too risky in high vol
        
        # Momentum Burst: Works in all regimes, best in trending/volatile
        if strategy == "MomentumBurst":
            if regime in ["TRENDING_UP", "TRENDING_DOWN", "VOLATILE"]:
                return True
            if regime == "RANGING":
                return True  # Breakouts from ranges are valid
        
        # Volatility Breakout: Works best in volatile regimes
        if strategy == "VolatilityBreakout":
            if regime == "VOLATILE":
                return True
            if regime == "TRENDING_UP" or regime == "TRENDING_DOWN":
                return True  # Trends often accompanied by vol
            if regime == "RANGING":
                return False  # Vol breakouts don't work in ranges
        
        # Default: allow if nothing else blocks
        return True
    
    def quality_score(self, signal) -> float:
        """
        Rate signal quality (0.0 to 1.0) considering all factors.
        Used for portfolio weighting if trading multiple strategies simultaneously.
        """
        
        score = signal.quality_score()
        
        # Bonus for multi-timeframe alignment
        if signal.tf_1m_signal and signal.tf_5m_confirmed and signal.tf_15m_bias in ['UP', 'DOWN']:
            score *= 1.15  # 15% bonus for full alignment
        
        # Penalty for weak confidence
        if signal.confidence < 0.65:
            score *= 0.8
        
        # Bonus for good risk/reward
        if signal.risk_reward_ratio and signal.risk_reward_ratio > 2.0:
            score *= 1.1
        
        return min(score, 1.0)
