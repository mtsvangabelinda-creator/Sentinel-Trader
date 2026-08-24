import logging
import logging.handlers
import os
from pathlib import Path
from config.settings import settings

def setup_logger(name: str) -> logging.Logger:
    """Setup structured logging for SentinelTrader"""
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # File handler (rotating)
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / f"{name}.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger
