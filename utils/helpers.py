import asyncio
import functools
import time
from typing import Callable, Any, TypeVar, Optional
import logging
import numpy as np

F = TypeVar("F", bound=Callable[..., Any])

logger = logging.getLogger(__name__)

def exponential_backoff(
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0
) -> Callable[[F], F]:
    """Exponential backoff retry decorator"""
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Max retries reached for {func.__name__}: {e}")
                        raise
                    
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}, "
                        f"retrying in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Max retries reached for {func.__name__}: {e}")
                        raise
                    
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}, "
                        f"retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator

def calculate_annualized_sharpe(returns: list, risk_free_rate: float = 0.05) -> float:
    """Calculate annualized Sharpe ratio (252 trading days)"""
    if not returns or len(returns) < 2:
        return 0.0
    
    returns = np.array(returns)
    excess_returns = returns - (risk_free_rate / 252)
    
    if excess_returns.std() == 0:
        return 0.0
    
    return float(np.sqrt(252) * excess_returns.mean() / excess_returns.std())

def calculate_max_drawdown(equity_curve: list) -> float:
    """Calculate maximum drawdown from equity curve"""
    if not equity_curve:
        return 0.0
    
    equity = np.array(equity_curve)
    peak = np.maximum.accumulate(equity)
    drawdown = (equity - peak) / peak
    
    return float(np.min(drawdown))

def calculate_icir(returns: list, benchmark_returns: Optional[list] = None) -> float:
    """Calculate Information Coefficient * Information Ratio"""
    if not returns or len(returns) < 2:
        return 0.0
    
    returns = np.array(returns)
    
    if benchmark_returns:
        excess_returns = returns - np.array(benchmark_returns)
    else:
        excess_returns = returns
    
    if excess_returns.std() == 0:
        return 0.0
    
    ic = excess_returns.mean() / excess_returns.std()
    return float(ic * np.sqrt(252))

async def gather_with_limit(coros: list, limit: int = 10) -> list:
    """Gather with concurrency limit"""
    semaphore = asyncio.Semaphore(limit)
    
    async def sem_coro(coro):
        async with semaphore:
            return await coro
    
    return await asyncio.gather(*(sem_coro(coro) for coro in coros))
