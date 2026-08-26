"""Retry mechanisms with exponential backoff and jitter for transient failures."""
import time
import asyncio
import random
from typing import Callable, TypeVar, Tuple, Type, Any, Optional
from core.logger import log

T = TypeVar("T")

def retry_sync(
    fn: Callable[..., T],
    max_retries: int = 3,
    initial_delay: float = 0.5,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int, float], None]] = None
) -> T:
    """Executes a synchronous function with exponential backoff retry on failure."""
    delay = initial_delay
    last_exception: Optional[Exception] = None

    for attempt in range(1, max_retries + 1):
        try:
            return fn()
        except exceptions as e:
            last_exception = e
            if attempt == max_retries:
                log.debug(f"[RetrySync] Failed after {max_retries} attempts: {e}")
                raise e

            sleep_time = delay * (1.0 + random.uniform(0, 0.1)) if jitter else delay
            if on_retry:
                on_retry(e, attempt, sleep_time)
            else:
                log.debug(f"[RetrySync] Attempt {attempt}/{max_retries} failed ({e}). Retrying in {sleep_time:.2f}s...")

            time.sleep(sleep_time)
            delay *= backoff_factor

    if last_exception:
        raise last_exception
    raise RuntimeError("Unexpected exit in retry_sync")

async def retry_async(
    coro_fn: Callable[..., Any],
    max_retries: int = 3,
    initial_delay: float = 0.5,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int, float], None]] = None
) -> Any:
    """Executes an asynchronous coroutine with exponential backoff retry on failure."""
    delay = initial_delay
    last_exception: Optional[Exception] = None

    for attempt in range(1, max_retries + 1):
        try:
            return await coro_fn()
        except exceptions as e:
            last_exception = e
            if attempt == max_retries:
                log.debug(f"[RetryAsync] Failed after {max_retries} attempts: {e}")
                raise e

            sleep_time = delay * (1.0 + random.uniform(0, 0.1)) if jitter else delay
            if on_retry:
                on_retry(e, attempt, sleep_time)
            else:
                log.debug(f"[RetryAsync] Attempt {attempt}/{max_retries} failed ({e}). Retrying in {sleep_time:.2f}s...")

            await asyncio.sleep(sleep_time)
            delay *= backoff_factor

    if last_exception:
        raise last_exception
    raise RuntimeError("Unexpected exit in retry_async")

__all__ = [
    "retry_sync",
    "retry_async",
]
