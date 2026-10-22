from __future__ import annotations
import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")

async def retry_async(operation: Callable[[], Awaitable[T]], *, attempts: int = 3,
                      base_delay: float = 0.1,
                      retry_on: tuple[type[BaseException], ...] = (TimeoutError, ConnectionError)) -> T:
    """Retry selected transient errors with exponential backoff."""
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    for attempt in range(attempts):
        try:
            return await operation()
        except retry_on:
            if attempt == attempts - 1:
                raise
            await asyncio.sleep(base_delay * (2 ** attempt))
    raise RuntimeError("unreachable")
