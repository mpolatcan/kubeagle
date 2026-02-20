"""Concurrent utilities - Semaphore and batching patterns for parallel operations.

This module provides utilities for managing concurrent operations:
- semaphore_operation: Context manager for semaphore-controlled operations
- batch_operations: Process items in batches with controlled concurrency
- RateLimiter: Token bucket rate limiter

Usage:
    # Semaphore-controlled operation
    async with semaphore_operation(semaphore):
        await long_running_task()

    # Batch operations
    results = await batch_operations(items, max_concurrent=4)

    # Rate limiter
    limiter = RateLimiter(rate=10, period=1.0)  # 10 ops/second
    await limiter.acquire()
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Coroutine, Iterable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ============================================================================
# Semaphore Utilities
# ============================================================================


@asynccontextmanager
async def semaphore_operation(
    semaphore: asyncio.Semaphore,
    *,
    timeout: float | None = None,
):
    """Context manager for semaphore-controlled operations.

    Acquires the semaphore before the operation and releases it after,
    even if the operation fails.

    Args:
        semaphore: The semaphore to acquire
        timeout: Optional timeout for acquiring the semaphore

    Usage:
        semaphore = asyncio.Semaphore(4)

        async with semaphore_operation(semaphore):
            await fetch_data()
    """
    acquired = False

    try:
        if timeout is not None:
            acquired = await asyncio.wait_for(semaphore.acquire(), timeout=timeout)
        else:
            await semaphore.acquire()
            acquired = True

        yield
    finally:
        if acquired:
            semaphore.release()


async def bounded_gather(
    coros: list[Coroutine[Any, Any, T]],
    semaphore: asyncio.Semaphore,
    *,
    return_exceptions: bool = False,
) -> list[Any]:
    """Run coroutines with bounded concurrency using a semaphore.

    Args:
        coros: List of coroutines to run
        semaphore: Semaphore limiting concurrent execution
        return_exceptions: Whether to return exceptions as results

    Returns:
        List of results in same order as input
    """
    async def run_with_semaphore(coro: Coroutine[Any, Any, T]) -> T:
        async with semaphore_operation(semaphore):
            return await coro

    return await asyncio.gather(
        *[run_with_semaphore(c) for c in coros],
        return_exceptions=return_exceptions,
    )


# ============================================================================
# Batch Operations
# ============================================================================


@dataclass
class BatchResult:
    """Result of a batch operation."""

    total_items: int
    successful: int
    failed: int
    errors: list[tuple[int, Exception]]
    results: list[Any]
    duration_ms: float


async def batch_operations(
    items: Iterable[T],
    operation: Callable[[T], Awaitable[Any]],
    *,
    max_concurrent: int = 4,
    batch_size: int | None = None,
    timeout: float | None = None,
) -> BatchResult:
    """Process items in batches with controlled concurrency.

    Args:
        items: Items to process
        operation: Async function to apply to each item
        max_concurrent: Maximum concurrent operations within a batch
        batch_size: Number of items per batch (defaults to max_concurrent)
        timeout: Optional timeout for each operation

    Returns:
        BatchResult with all results and statistics

    Usage:
        results = await batch_operations(
            items,
            operation=process_item,
            max_concurrent=4,
        )
    """
    import time

    if batch_size is None:
        batch_size = max_concurrent

    semaphore = asyncio.Semaphore(max_concurrent)
    item_list = list(items)
    total_items = len(item_list)
    results: list[Any] = []
    errors: list[tuple[int, Exception]] = []
    start_time = time.monotonic()

    # Process in batches
    for batch_start in range(0, total_items, batch_size):
        batch_end = min(batch_start + batch_size, total_items)
        batch = item_list[batch_start:batch_end]

        # Create tasks for this batch
        async def process_with_index(idx: int, item: T) -> tuple[int, Any]:
            try:
                async with semaphore_operation(semaphore, timeout=timeout):
                    result = await operation(item)
                    return (idx, result)
            except Exception as e:
                return (idx, e)

        batch_tasks = [process_with_index(batch_start + i, item) for i, item in enumerate(batch)]

        # Run batch
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

        # Collect results
        for res in batch_results:
            if isinstance(res, tuple) and len(res) == 2:
                idx, value = res
                if isinstance(value, Exception):
                    errors.append((idx, value))
                else:
                    results.append(value)

    duration_ms = (time.monotonic() - start_time) * 1000

    return BatchResult(
        total_items=total_items,
        successful=len(results),
        failed=len(errors),
        errors=errors,
        results=results,
        duration_ms=duration_ms,
    )


# ============================================================================
# Rate Limiter
# ============================================================================


class RateLimiter:
    """Token bucket rate limiter for controlling request rate.

    Attributes:
        rate: Tokens per period
        period: Period in seconds
        available_tokens: Current available tokens
        last_refill: Timestamp of last refill

    Usage:
        limiter = RateLimiter(rate=10, period=1.0)  # 10 per second

        for item in items:
            await limiter.acquire()
            await make_request(item)
    """

    def __init__(
        self,
        rate: float,
        period: float = 1.0,
        *,
        initial_tokens: float | None = None,
        max_tokens: float | None = None,
    ) -> None:
        """Initialize the rate limiter.

        Args:
            rate: Tokens per period
            period: Period in seconds
            initial_tokens: Initial available tokens (defaults to rate)
            max_tokens: Maximum tokens (defaults to rate)
        """
        self.rate = rate
        self.period = period

        self.max_tokens = max_tokens if max_tokens is not None else rate
        self.available_tokens = initial_tokens if initial_tokens is not None else rate

        self.last_refill = 0.0  # Will be set on first acquire()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: float = 1.0) -> float:
        """Acquire tokens from the limiter.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            Wait time in seconds before tokens are available
        """
        wait_time = 0.0

        # Compute wait time under the lock, but release before sleeping
        # so other callers are not serialized behind our sleep.
        async with self._lock:
            now = asyncio.get_running_loop().time()

            # Calculate time since last refill
            elapsed = now - self.last_refill if self.last_refill > 0 else 0.0
            self.last_refill = now

            # Add new tokens based on elapsed time
            tokens_to_add = (elapsed / self.period) * self.rate
            self.available_tokens = min(
                self.max_tokens,
                self.available_tokens + tokens_to_add,
            )

            # Reserve tokens and compute wait time
            if self.available_tokens < tokens:
                tokens_needed = tokens - self.available_tokens
                wait_time = (tokens_needed / self.rate) * self.period
                self.available_tokens = 0.0
            else:
                self.available_tokens -= tokens

        # Sleep outside the lock so concurrent callers can proceed
        if wait_time > 0:
            await asyncio.sleep(wait_time)

        return wait_time

    async def __aenter__(self) -> RateLimiter:
        """Context manager entry."""
        await self.acquire()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Context manager exit."""
        pass


__all__ = [
    "semaphore_operation",
    "bounded_gather",
    "batch_operations",
    "BatchResult",
    "RateLimiter",
]
