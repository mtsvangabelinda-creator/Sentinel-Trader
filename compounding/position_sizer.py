"""
Position sizing with Kelly Criterion and adaptive RL adjustments
"""
from typing import Dict, Optional
from utils.logger import setup_logger
from signal_engine.game_theory_filters import GameTheoryFilters
from adaptive.rl_agent import RLAgent
from config.settings import settings

logger = setup_logger(__name__)

class PositionSizer:
    """Adaptive position sizing for SentinelTrader"""
    
    def __init__(self, strategy: str, account_balance: float):
        self.strategy = strategy
        self.account_balance = account_balance
        self.rl_agent = RLAgent(strategy)
    
    async def calculate_position_size(
        self,
        entry_price: float,
        stop_loss: float,
        win_rate: float = 0.55,
        avg_win: float = 1.02,
        avg_loss: float = 0.98,
        market_state: Optional[Dict] = None
    ) -> float:
        """
        Calculate position size using Kelly Criterion + RL adjustment
        
        Returns: quantity to purchase
        """
        
        if entry_price <= 0:
            return 0.0
        
        # Base position size (% of account)
        base_pct = settings.MAX_POSITION_SIZE_PCT
        
        # Kelly Criterion adjustment
        kelly_f = GameTheoryFilters.kelly_criterion(win_rate, avg_win, avg_loss)
        adjusted_pct = base_pct * kelly_f / 0.25  # Normalize
        
        # RL adjustment
        rl_multiplier = 1.0
        if market_state:
            rl_multiplier = await self.rl_agent.predict_position_size(market_state)
        
        final_pct = adjusted_pct * rl_multiplier
        final_pct = min(final_pct, settings.MAX_POSITION_SIZE_PCT)
        final_pct = max(final_pct, 0.01)  # Minimum 1%
        
        # Calculate quantity
        position_value = self.account_balance * final_pct
        quantity = position_value / entry_price
        
        logger.info(
            f"Position size: {quantity:.4f} "
            f"({final_pct*100:.1f}% of account @ ${entry_price:.2f})"
        )
        
        return quantity
