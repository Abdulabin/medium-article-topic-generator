"""Retry logic for API calls with exponential backoff."""

from functools import wraps
from typing import Callable, TypeVar, ParamSpec
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import logging

from medium_topic_agent.utils.logger import get_logger

logger = get_logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


def with_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    retry_exceptions: tuple = (Exception,),
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator for retrying failed operations with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts.
        min_wait: Minimum wait time between retries in seconds.
        max_wait: Maximum wait time between retries in seconds.
        retry_exceptions: Tuple of exception types to retry on.
        
    Returns:
        Decorated function with retry logic.
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_if_exception_type(retry_exceptions),
            before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING),
        )
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return func(*args, **kwargs)
        return wrapper
    return decorator


async def async_with_retry(
    func: Callable[P, T],
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
) -> T:
    """Async retry wrapper for coroutines.
    
    Args:
        func: Async function to retry.
        max_attempts: Maximum number of retry attempts.
        min_wait: Minimum wait time between retries.
        max_wait: Maximum wait time between retries.
        
    Returns:
        Result of the function call.
    """
    import asyncio
    
    last_exception = None
    wait_time = min_wait
    
    for attempt in range(max_attempts):
        try:
            return await func()
        except Exception as e:
            last_exception = e
            logger.warning(
                "retry_attempt",
                attempt=attempt + 1,
                max_attempts=max_attempts,
                error=str(e),
                wait_time=wait_time,
            )
            if attempt < max_attempts - 1:
                await asyncio.sleep(wait_time)
                wait_time = min(wait_time * 2, max_wait)
    
    raise last_exception
