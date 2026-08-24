import os
from typing import Optional
from dotenv import load_dotenv
import logging

load_dotenv()

class Settings:
    """Global configuration for SentinelTrader"""
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # API Credentials
    KRAKEN_API_KEY: str = os.getenv("KRAKEN_API_KEY", "")
    KRAKEN_API_SECRET: str = os.getenv("KRAKEN_API_SECRET", "")
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://sentineltrader_user:sentineltrader_password@localhost:5432/sentineltrader_db"
    )
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Trading Parameters
    INITIAL_CAPITAL: float = float(os.getenv("INITIAL_CAPITAL", "300"))
    MAX_POSITION_SIZE_PCT: float = float(os.getenv("MAX_POSITION_SIZE_PCT", "0.10"))
    MAX_DAILY_LOSS_PCT: float = float(os.getenv("MAX_DAILY_LOSS_PCT", "0.05"))
    MAX_DRAWDOWN_PCT: float = float(os.getenv("MAX_DRAWDOWN_PCT", "0.10"))
    
    # Strategy Configuration
    ARBITRAGE_ASSETS: list = ["BTC", "ETH", "SOL", "XRP", "ADA", "DOT", "LINK"]
    MEME_ASSETS: list = ["WIF", "PEPE", "BONK", "DOGE", "SHIB"]
    
    MIN_MARKET_CAP_ARBITRAGE: float = 5e9  # $5B
    MAX_MARKET_CAP_MEME: float = 500e6  # $500M
    MIN_LIQUIDITY_CEX: float = 10e6  # $10M
    MIN_LIQUIDITY_DEX: float = 10e3  # $10K
    
    # Regime Detection
    REGIME_CHECK_INTERVAL: int = 900  # 15 minutes
    HMM_N_COMPONENTS: int = 3
    
    # Genetic Programming
    EVOLVE_DAILY_HOUR: int = 0  # Midnight UTC
    COMPLEXITY_PENALTY: float = 0.05
    MIN_TRADES_OOS: int = 20
    ROLLING_ICIR_THRESHOLD: float = 0.2
    ICIR_FAIL_WINDOW: int = 3  # days
    
    # RL Agent
    RL_LEARNING_RATE: float = 1e-4
    RL_GAMMA: float = 0.99
    RL_GAE_LAMBDA: float = 0.95
    RL_CLIP_RATIO: float = 0.2
    RL_BATCH_SIZE: int = 64
    RL_EPOCHS_PER_UPDATE: int = 10
    
    # Risk Management
    DAILY_LOSS_LIMIT_PCT: float = 0.05  # -5%
    MAX_DRAWDOWN: float = 0.10  # -10%
    REALLOCATION_LOCK_DAYS: int = 120
    
    # Oversight Loop
    OVERSIGHT_CHECK_INTERVAL: int = 3600  # 1 hour
    UNDERPERFORMER_THRESHOLD: float = 0.2
    
    # Data & Caching
    WHITELIST_CACHE_TTL: int = 86400  # 24 hours
    DATA_RETENTION_DAYS: int = 365
    
    # Execution
    ORDER_TIMEOUT_SECONDS: int = 30
    LIFECYCLE_CHECK_INTERVAL: int = 5  # seconds
    FORCE_CLOSE_HOUR_MEME: int = 23  # 23:00 UTC
    
    @classmethod
    def validate(cls) -> None:
        """Validate critical settings"""
        if not cls.KRAKEN_API_KEY or not cls.KRAKEN_API_SECRET:
            if cls.ENVIRONMENT == "production":
                raise ValueError("Kraken API credentials required for production")
        
        if not cls.TELEGRAM_BOT_TOKEN:
            if cls.ENVIRONMENT == "production":
                raise ValueError("Telegram bot token required for production")

settings = Settings()
