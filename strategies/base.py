from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class Signal:
    """Multi-timeframe trading signal with confirmation levels."""
    
    # Primary signal (1m timeframe)
    action: str  # 'BUY', 'SELL', 'HOLD'
    confidence: float  # 0.0 to 1.0
    
    # Timeframe confirmations
    tf_1m_signal: bool  # 1m candle triggered signal
    tf_5m_confirmed: bool  # 5m confirms direction/momentum
    tf_15m_bias: str  # 'UP', 'DOWN', 'NEUTRAL' - market direction
    
    # Entry details
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size: Optional[float] = None
    
    # Risk/reward
    risk_reward_ratio: Optional[float] = None
    
    # Metadata
    strategy_name: str = "Unknown"
    timestamp: Optional[str] = None
    reason: str = ""  # Human-readable reason for signal
    
    # Multi-timeframe details
    timeframe_scores: Dict[str, float] = None  # {'1m': 0.8, '5m': 0.7, '15m': 0.9}
    
    def __post_init__(self):
        if self.timeframe_scores is None:
            self.timeframe_scores = {}
    
    def is_valid(self) -> bool:
        """Check if signal meets minimum criteria."""
        # Signal must have action
        if self.action not in ['BUY', 'SELL', 'HOLD']:
            return False
        
        # For BUY/SELL, need confirmation across timeframes
        if self.action in ['BUY', 'SELL']:
            # Must have 1m signal AND 5m confirmation
            if not (self.tf_1m_signal and self.tf_5m_confirmed):
                return False
            
            # 15m bias must align with action
            if self.action == 'BUY' and self.tf_15m_bias != 'UP':
                return False
            if self.action == 'SELL' and self.tf_15m_bias != 'DOWN':
                return False
            
            # Minimum confidence threshold
            if self.confidence < 0.6:
                return False
        
        return True
    
    def quality_score(self) -> float:
        """
        Calculate overall signal quality (0.0 to 1.0).
        Higher score = higher conviction.
        """
        score = 0.0
        
        # Base confidence (50% weight)
        score += self.confidence * 0.5
        
        # Timeframe alignment (40% weight)
        alignment = 0.0
        if self.tf_1m_signal:
            alignment += 0.33
        if self.tf_5m_confirmed:
            alignment += 0.33
        if self.tf_15m_bias in ['UP', 'DOWN']:  # Any bias is better than NEUTRAL
            alignment += 0.34
        
        score += alignment * 0.4
        
        # Risk/reward (10% weight)
        if self.risk_reward_ratio:
            # Scale RR ratio: 1.0 RR = 0.5 score, 3.0 RR = 1.0 score
            rr_score = min(self.risk_reward_ratio / 3.0, 1.0)
            score += rr_score * 0.1
        
        return min(score, 1.0)
