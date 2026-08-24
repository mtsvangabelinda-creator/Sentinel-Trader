"""
Signal aggregator combines all signal sources for SentinelTrader
"""
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
from utils.logger import setup_logger
from signal_engine.zscore_calculator import ZScoreCalculator
from signal_engine.game_theory_filters import GameTheoryFilters
from signal_engine.scoring import SignalScorer
from database.queries import Queries

logger = setup_logger(__name__)

class SignalAggregator:
    """Aggregate signals from multiple sources"""
    
    def __init__(self, strategy: str):
        self.strategy = strategy
        self.current_signals: List[Dict] = []
    
    async def aggregate(self, market_data: Dict, regime: int, evolved_alpha: Optional[float]) -> List[Dict]:
        """Aggregate all signal sources"""
        
        signals = []
        
        # 1. Evolved Alpha Signal
        if evolved_alpha is not None:
            alpha_signal = {
                "source": "evolved_alpha",
                "value": evolved_alpha,
                "weight": 0.3
            }
            signals.append(alpha_signal)
        
        # 2. Z-Score Signal
        if "close" in market_data and isinstance(market_data["close"], (list, pd.Series)):
            try:
                z_score_value = market_data.get("z_score", 0)
                if isinstance(z_score_value, (int, float)):
                    z_signal = {
                        "source": "zscore",
                        "value": z_score_value,
                        "weight": 0.3
                    }
                    signals.append(z_signal)
            except Exception as e:
                logger.debug(f"Z-Score signal error: {e}")
        
        # 3. Game Theory Score
        entry_price = market_data.get("close", 0)
        if entry_price > 0:
            gt_score = GameTheoryFilters.competitive_payoff_score(
                entry_price=entry_price,
                tp=entry_price * 1.05,
                sl=entry_price * 0.95,
                win_prob=0.55
            )
            gt_signal = {
                "source": "game_theory",
                "value": gt_score,
                "weight": 0.25
            }
            signals.append(gt_signal)
        
        # 4. Volume Signal
        volume_score = min(market_data.get("volume", 0) / 1e6, 1.0)
        vol_signal = {
            "source": "volume",
            "value": volume_score,
            "weight": 0.15
        }
        signals.append(vol_signal)
        
        # Calculate composite score
        total_weight = sum(s["weight"] for s in signals)
        if total_weight > 0:
            composite = sum(s["value"] * s["weight"] for s in signals) / total_weight
        else:
            composite = 0.0
        
        # Save signal to database
        try:
            await Queries.save_signal(
                self.strategy,
                market_data.get("asset", "UNKNOWN"),
                "entry" if composite > 0.3 else "neutral",
                composite,
                regime,
                evolved_alpha or 0
            )
        except Exception as e:
            logger.debug(f"Failed to save signal: {e}")
        
        self.current_signals = signals
        
        return signals

import pandas as pd
