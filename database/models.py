"""
Database models and schema initialization for SentinelTrader
"""

SCHEMA = """
-- Regime States
CREATE TABLE IF NOT EXISTS regime_states (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    regime INTEGER NOT NULL,
    hmm_log_likelihood FLOAT,
    market_condition TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Evolved Alpha Expressions
CREATE TABLE IF NOT EXISTS evolved_alphas (
    id SERIAL PRIMARY KEY,
    strategy TEXT NOT NULL,
    expression TEXT NOT NULL,
    parameters JSONB,
    icir FLOAT,
    trades_count INTEGER,
    oos_start_date DATE,
    oos_end_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Signals
CREATE TABLE IF NOT EXISTS signals (
    id SERIAL PRIMARY KEY,
    strategy TEXT NOT NULL,
    asset TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    z_score FLOAT,
    regime INTEGER,
    confidence FLOAT,
    alpha_value FLOAT,
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trades
CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    strategy TEXT NOT NULL,
    asset TEXT NOT NULL,
    entry_price FLOAT NOT NULL,
    exit_price FLOAT,
    entry_time TIMESTAMP NOT NULL,
    exit_time TIMESTAMP,
    quantity FLOAT NOT NULL,
    pnl FLOAT,
    pnl_pct FLOAT,
    stop_loss FLOAT,
    take_profit FLOAT,
    status TEXT DEFAULT 'open',
    order_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Positions
CREATE TABLE IF NOT EXISTS positions (
    id SERIAL PRIMARY KEY,
    strategy TEXT NOT NULL,
    asset TEXT NOT NULL,
    quantity FLOAT NOT NULL,
    entry_price FLOAT NOT NULL,
    current_price FLOAT,
    unrealized_pnl FLOAT,
    entry_time TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Performance Metrics
CREATE TABLE IF NOT EXISTS performance_metrics (
    id SERIAL PRIMARY KEY,
    strategy TEXT NOT NULL,
    date DATE NOT NULL,
    daily_return FLOAT,
    cumulative_return FLOAT,
    sharpe_ratio FLOAT,
    max_drawdown FLOAT,
    win_rate FLOAT,
    trade_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(strategy, date)
);

-- RL Agent State
CREATE TABLE IF NOT EXISTS rl_agent_state (
    id SERIAL PRIMARY KEY,
    strategy TEXT NOT NULL,
    position_size_weight FLOAT,
    exit_timing_bias FLOAT,
    holding_period_bias FLOAT,
    model_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Risk Events
CREATE TABLE IF NOT EXISTS risk_events (
    id SERIAL PRIMARY KEY,
    strategy TEXT NOT NULL,
    event_type TEXT NOT NULL,
    severity TEXT,
    description TEXT,
    action_taken TEXT,
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Whitelist Cache
CREATE TABLE IF NOT EXISTS whitelist_cache (
    id SERIAL PRIMARY KEY,
    asset TEXT UNIQUE NOT NULL,
    is_tradable BOOLEAN,
    min_order_cost FLOAT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- RL Training Log
CREATE TABLE IF NOT EXISTS rl_training_log (
    id SERIAL PRIMARY KEY,
    strategy TEXT NOT NULL,
    episode INTEGER,
    total_reward FLOAT,
    avg_loss FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_trades_strategy_asset ON trades(strategy, asset);
CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON trades(entry_time);
CREATE INDEX IF NOT EXISTS idx_signals_strategy_asset ON signals(strategy, asset);
CREATE INDEX IF NOT EXISTS idx_regime_states_timestamp ON regime_states(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_strategy_date ON performance_metrics(strategy, date DESC);
"""
