"""
Regime detection using Hidden Markov Model (HMM)
Classifies market state: Bullish, Neutral, Bearish
"""
import numpy as np
import pandas as pd
from typing import Optional, Tuple, List, Dict
from datetime import datetime, timedelta
from hmmlearn import hmm
from utils.logger import setup_logger
from database.connection import db
from database.queries import Queries
from config.settings import settings

logger = setup_logger(__name__)

class RegimeDetector:
    """Detect market regime using HMM"""
    
    def __init__(self):
        self.model: Optional[hmm.GaussianHMM] = None
        self.n_components = settings.HMM_N_COMPONENTS
        self.current_regime = 0
    
    async def train(self, price_data: List[float]) -> bool:
        """Train HMM on price data"""
        try:
            if len(price_data) < 100:
                logger.warning(f"Insufficient data for HMM training: {len(price_data)}")
                return False
            
            # Calculate returns
            prices = np.array(price_data)
            returns = np.diff(np.log(prices)).reshape(-1, 1)
            
            # Train HMM
            self.model = hmm.GaussianHMM(
                n_components=self.n_components,
                covariance_type="diag",
                n_iter=1000,
                random_state=42
            )
            
            self.model.fit(returns)
            
            logger.info(f"HMM trained with {self.n_components} components")
            logger.info(f"Means: {self.model.means_}")
            
            return True
        except Exception as e:
            logger.error(f"HMM training failed: {e}")
            return False
    
    async def predict(self, price_data: List[float]) -> Tuple[int, float]:
        """
        Predict current regime
        Returns: (regime, log_likelihood)
        """
        if not self.model or len(price_data) < 10:
            return 0, 0.0
        
        try:
            prices = np.array(price_data[-100:])  # Use last 100 prices
            returns = np.diff(np.log(prices)).reshape(-1, 1)
            
            regime = self.model.predict(returns)[-1]
            likelihood = self.model.score(returns)
            
            self.current_regime = regime
            
            # Save to database
            regime_names = ["Bearish", "Neutral", "Bullish"]
            condition = regime_names[min(regime, 2)]
            
            await Queries.save_regime_state(regime, likelihood, condition)
            
            logger.debug(f"Regime: {condition} (likelihood={likelihood:.4f})")
            
            return regime, likelihood
        except Exception as e:
            logger.error(f"Regime prediction failed: {e}")
            return self.current_regime, 0.0
    
    def get_regime_context(self) -> Dict:
        """Get trading context based on regime"""
        regime_configs = {
            0: {  # Bearish
                "name": "Bearish",
                "position_multiplier": 0.7,
                "take_profit_tightness": 0.8,
                "stop_loss_tightness": 1.2,
            },
            1: {  # Neutral
                "name": "Neutral",
                "position_multiplier": 1.0,
                "take_profit_tightness": 1.0,
                "stop_loss_tightness": 1.0,
            },
            2: {  # Bullish
                "name": "Bullish",
                "position_multiplier": 1.3,
                "take_profit_tightness": 1.2,
                "stop_loss_tightness": 0.8,
            }
        }
        
        return regime_configs.get(self.current_regime, regime_configs[1])
