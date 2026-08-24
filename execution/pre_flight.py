"""
Pre-flight checks before order execution for SentinelTrader
"""
from typing import Dict, Tuple
from utils.logger import setup_logger
from config.settings import settings

logger = setup_logger(__name__)

class PreFlightChecker:
    """Validate trades before execution"""
    
    @staticmethod
    def check_trade(
        strategy: str,
        asset: str,
        quantity: float,
        entry_price: float,
        sl: float,
        tp: float
    ) -> Tuple[bool, str]:
        """
        Pre-flight checks:
        1. Position size not too large
        2. Stop loss and take profit set correctly
        3. Order would not violate risk limits
        """
        
        # Check quantity
        if quantity <= 0:
            return False, "Invalid quantity"
        
        max_position = settings.INITIAL_CAPITAL * settings.MAX_POSITION_SIZE_PCT / entry_price
        if quantity > max_position:
            return False, f"Position size exceeds limit ({quantity:.4f} > {max_position:.4f})"
        
        # Check SL and TP
        if sl >= entry_price or tp <= entry_price:
            return False, f"Invalid SL ({sl}) or TP ({tp}) relative to entry ({entry_price})"
        
        # Check risk/reward
        risk = abs(entry_price - sl) / entry_price
        reward = abs(tp - entry_price) / entry_price
        
        if reward < risk:
            return False, f"Poor risk/reward ratio ({reward:.2%} / {risk:.2%})"
        
        # Check order viability
        if entry_price <= 0:
            return False, "Invalid entry price"
        
        logger.info(
            f"Pre-flight check passed: {asset} "
            f"Qty={quantity:.4f} Risk={risk*100:.1f}% Reward={reward*100:.1f}%"
        )
        
        return True, "OK"
