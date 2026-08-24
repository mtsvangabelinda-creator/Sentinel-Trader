"""
Test execution module for SentinelTrader
"""
import pytest
from execution.pre_flight import PreFlightChecker

def test_preflight_checks_valid():
    """Test pre-flight validation with valid trade"""
    
    passed, msg = PreFlightChecker.check_trade(
        strategy="arbitrage",
        asset="BTC",
        quantity=0.1,
        entry_price=40000,
        sl=39000,
        tp=41000
    )
    
    assert passed is True
    assert msg == "OK"

def test_invalid_quantity():
    """Test invalid quantity"""
    
    passed, msg = PreFlightChecker.check_trade(
        strategy="arbitrage",
        asset="BTC",
        quantity=0,
        entry_price=40000,
        sl=39000,
        tp=41000
    )
    
    assert passed is False

def test_invalid_stop_loss():
    """Test invalid stop loss"""
    
    passed, msg = PreFlightChecker.check_trade(
        strategy="arbitrage",
        asset="BTC",
        quantity=0.1,
        entry_price=40000,
        sl=41000,  # Invalid: SL > entry
        tp=41000
    )
    
    assert passed is False

def test_invalid_take_profit():
    """Test invalid take profit"""
    
    passed, msg = PreFlightChecker.check_trade(
        strategy="arbitrage",
        asset="BTC",
        quantity=0.1,
        entry_price=40000,
        sl=39000,
        tp=40000  # Invalid: TP = entry
    )
    
    assert passed is False

def test_poor_risk_reward():
    """Test poor risk/reward ratio"""
    
    passed, msg = PreFlightChecker.check_trade(
        strategy="arbitrage",
        asset="BTC",
        quantity=0.1,
        entry_price=40000,
        sl=39500,  # 1.25% risk
        tp=40100   # 0.25% reward (poor)
    )
    
    assert passed is False

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
