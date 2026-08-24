"""
Test game theory filters
"""
import pytest
from signal_engine.game_theory_filters import GameTheoryFilters

def test_kelly_criterion():
    """Test Kelly Criterion calculation"""
    
    kelly = GameTheoryFilters.kelly_criterion(
        win_rate=0.55,
        avg_win=1.02,
        avg_loss=0.98
    )
    
    assert 0 <= kelly <= 0.50
    assert isinstance(kelly, float)

def test_kelly_criterion_even_odds():
    """Test Kelly with even odds"""
    
    kelly = GameTheoryFilters.kelly_criterion(
        win_rate=0.5,
        avg_win=1.0,
        avg_loss=1.0
    )
    
    assert kelly == 0.0

def test_competitive_payoff():
    """Test competitive payoff score"""
    
    score = GameTheoryFilters.competitive_payoff_score(
        entry_price=100,
        tp=105,
        sl=95,
        win_prob=0.55
    )
    
    assert score >= 0
    assert isinstance(score, float)

def test_cooperative_clustering():
    """Test cooperative clustering score"""
    
    score = GameTheoryFilters.cooperative_clustering_score(
        similar_signals=8,
        total_signals=10
    )
    
    assert 0 <= score <= 1.0
    assert score == 0.8

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
