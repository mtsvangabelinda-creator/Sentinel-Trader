"""
Common database queries for SentinelTrader
"""
from typing import List, Dict, Optional
from database.connection import db
from datetime import datetime, timedelta

class Queries:
    """Database queries"""
    
    @staticmethod
    async def get_recent_trades(strategy: str, limit: int = 50) -> List[Dict]:
        """Get recent trades for strategy"""
        query = """
            SELECT * FROM trades
            WHERE strategy = $1
            ORDER BY entry_time DESC
            LIMIT $2
        """
        return await db.fetch(query, strategy, limit)
    
    @staticmethod
    async def get_open_positions(strategy: str) -> List[Dict]:
        """Get open positions"""
        query = """
            SELECT * FROM positions
            WHERE strategy = $1
        """
        return await db.fetch(query, strategy)
    
    @staticmethod
    async def get_performance_summary(strategy: str, days: int = 30) -> Dict:
        """Get performance summary for last N days"""
        query = """
            SELECT
                SUM(daily_return) as total_return,
                AVG(sharpe_ratio) as avg_sharpe,
                MIN(max_drawdown) as max_dd,
                AVG(win_rate) as avg_win_rate,
                SUM(trade_count) as total_trades
            FROM performance_metrics
            WHERE strategy = $1
            AND date >= CURRENT_DATE - INTERVAL '%s days'
        """
        result = await db.fetchrow(query, strategy, days)
        return result if result else {}
    
    @staticmethod
    async def save_trade(trade_data: Dict) -> int:
        """Save new trade"""
        query = """
            INSERT INTO trades
            (strategy, asset, entry_price, quantity, entry_time, status, order_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
        """
        return await db.fetchval(
            query,
            trade_data["strategy"],
            trade_data["asset"],
            trade_data["entry_price"],
            trade_data["quantity"],
            trade_data["entry_time"],
            "open",
            trade_data.get("order_id")
        )
    
    @staticmethod
    async def close_trade(trade_id: int, exit_price: float, exit_time: datetime, pnl: float):
        """Close trade"""
        query = """
            UPDATE trades
            SET exit_price = $1, exit_time = $2, status = 'closed', pnl = $3
            WHERE id = $4
        """
        await db.execute(query, exit_price, exit_time, pnl, trade_id)
    
    @staticmethod
    async def get_regime_state() -> Optional[Dict]:
        """Get latest regime state"""
        query = """
            SELECT * FROM regime_states
            ORDER BY timestamp DESC
            LIMIT 1
        """
        return await db.fetchrow(query)
    
    @staticmethod
    async def save_regime_state(regime: int, hmm_likelihood: float, condition: str):
        """Save regime state"""
        query = """
            INSERT INTO regime_states
            (timestamp, regime, hmm_log_likelihood, market_condition)
            VALUES (CURRENT_TIMESTAMP, $1, $2, $3)
        """
        await db.execute(query, regime, hmm_likelihood, condition)
    
    @staticmethod
    async def get_active_alphas(strategy: str) -> List[Dict]:
        """Get active alpha expressions"""
        query = """
            SELECT * FROM evolved_alphas
            WHERE strategy = $1 AND is_active = TRUE
        """
        return await db.fetch(query, strategy)
    
    @staticmethod
    async def save_performance_metrics(metrics: Dict):
        """Save daily performance metrics"""
        query = """
            INSERT INTO performance_metrics
            (strategy, date, daily_return, cumulative_return, sharpe_ratio, max_drawdown, win_rate, trade_count)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (strategy, date) DO UPDATE SET
                daily_return = EXCLUDED.daily_return,
                cumulative_return = EXCLUDED.cumulative_return,
                sharpe_ratio = EXCLUDED.sharpe_ratio,
                max_drawdown = EXCLUDED.max_drawdown,
                win_rate = EXCLUDED.win_rate,
                trade_count = EXCLUDED.trade_count
        """
        await db.execute(
            query,
            metrics["strategy"],
            datetime.utcnow().date(),
            metrics.get("daily_return", 0),
            metrics.get("cumulative_return", 0),
            metrics.get("sharpe_ratio", 0),
            metrics.get("max_drawdown", 0),
            metrics.get("win_rate", 0),
            metrics.get("trade_count", 0)
        )
    
    @staticmethod
    async def save_signal(strategy: str, asset: str, signal_type: str, score: float, regime: int, alpha: float):
        """Save signal"""
        query = """
            INSERT INTO signals
            (strategy, asset, signal_type, z_score, regime, confidence, alpha_value, timestamp)
            VALUES ($1, $2, $3, $4, $5, $6, $7, CURRENT_TIMESTAMP)
        """
        await db.execute(query, strategy, asset, signal_type, score, regime, abs(score), alpha)
    
    @staticmethod
    async def save_risk_event(strategy: str, event_type: str, severity: str, description: str, action: str):
        """Save risk event"""
        query = """
            INSERT INTO risk_events
            (strategy, event_type, severity, description, action_taken, timestamp)
            VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP)
        """
        await db.execute(query, strategy, event_type, severity, description, action)
