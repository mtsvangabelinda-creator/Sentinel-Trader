"""
Test Z-Score calculations
"""
import pytest
import pandas as pd
import numpy as np
from signal_engine.zscore_calculator import ZScoreCalculator

def test_zscore_calculation():
    """Test Z-Score calculation"""
    
    prices = [100, 101, 102, 103, 104, 105, 104, 103, 102, 101]
    df = pd.DataFrame({"close": prices})
    
    z_scores = ZScoreCalculator.calculate(df)
    
    assert len(z_scores) == len(prices)
    assert not z_scores.isna().all()

def test_mean_reversion_signal():
    """Test mean reversion signal generation"""
    
    z_scores = pd.Series([2.5, 2.0, 1.5, 0.5, -0.5, -1.5, -2.0, -2.5, -1.5, 0.5])
    
    signal = ZScoreCalculator.mean_reversion_signal(z_scores)
    
    assert len(signal) == len(z_scores)
    assert signal.dtype in [np.int64, np.int32, np.float64]

def test_momentum_signal():
    """Test momentum signal generation"""
    
    z_scores = pd.Series([0.5, 1.0, 1.5, 2.0, 2.5, 2.0, 1.5, 1.0, 0.5, 0.0])
    
    signal = ZScoreCalculator.momentum_signal(z_scores)
    
    assert len(signal) == len(z_scores)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
