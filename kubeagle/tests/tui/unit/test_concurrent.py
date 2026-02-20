"""Tests for concurrent utilities - semaphore and batching patterns.

This module tests:
- semaphore_operation context manager
- bounded_gather bounded concurrency
- batch_operations batching with concurrency
- RateLimiter token bucket rate limiting
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import MagicMock

import pytest

from kubeagle.utils.concurrent import (
    BatchResult,
    RateLimiter,
    batch_operations,
    bounded_gather,
    semaphore_operation,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def small_semaphore() -> asyncio.Semaphore:
    """Create a small semaphore for testing."""
    return asyncio.Semaphore(2)


# =============================================================================
# Concurrent Utilities Unit Tests
# =============================================================================


class TestConcurrentImports:
    """Test that concurrent utilities can be imported correctly."""

    def test_semaphore_operation_import(self) -> None:
        """Test semaphore_operation function import."""
        from kubeagle.utils.concurrent import semaphore_operation

        assert semaphore_operation is not None

    def test_bounded_gather_import(self) -> None:
        """Test bounded_gather function import."""
        from kubeagle.utils.concurrent import bounded_gather

        assert bounded_gather is not None

    def test_batch_operations_import(self) -> None:
        """Test batch_operations function import."""
        from kubeagle.utils.concurrent import batch_operations

        assert batch_operations is not None

    def test_batch_result_import(self) -> None:
        """Test BatchResult dataclass import."""
        from kubeagle.utils.concurrent import BatchResult

        result = BatchResult(
            total_items=10, successful=8, failed=2, errors=[], results=[], duration_ms=100.0
        )
        assert result.total_items == 10
        assert result.successful == 8
        assert result.failed == 2

    @pytest.mark.asyncio
    async def test_rate_limiter_import(self) -> None:
        """Test RateLimiter class import."""
        from kubeagle.utils.concurrent import RateLimiter

        limiter = RateLimiter(rate=10, period=1.0)
        assert limiter.rate == 10


class TestSemaphoreOperation:
    """Test semaphore_operation context manager."""

    @pytest.mark.asyncio
    async def test_acquires_and_releases_with_timeout(self) -> None:
        """Test that semaphore is acquired and released (using timeout path)."""
        semaphore = asyncio.Semaphore(1)  # Use value 1 so locked() works correctly
        acquired = False
        released = False

        async with semaphore_operation(semaphore, timeout=1.0):
            acquired = True
            # Verify semaphore is acquired (value becomes 0, locked() returns True)
            assert semaphore.locked() is True

        released = True
        # Verify semaphore is released (value becomes 1, locked() returns False)
        assert semaphore.locked() is False

        assert acquired and released

    @pytest.mark.asyncio
    async def test_releases_on_exception(self) -> None:
        """Test that semaphore is released even on exception (using timeout path)."""
        semaphore = asyncio.Semaphore(1)

        with pytest.raises(ValueError):
            async with semaphore_operation(semaphore, timeout=1.0):
                raise ValueError("Test exception")

        # Semaphore should be released
        assert semaphore.locked() is False

    @pytest.mark.asyncio
    async def test_with_timeout_success(self) -> None:
        """Test semaphore_operation with timeout (success case)."""
        semaphore = asyncio.Semaphore(1)

        async with semaphore_operation(semaphore, timeout=1.0):
            pass

        # Semaphore should be released
        assert semaphore.locked() is False

    @pytest.mark.asyncio
    async def test_multiple_concurrent_operations(self) -> None:
        """Test multiple concurrent operations with semaphore (using timeout path)."""
        semaphore = asyncio.Semaphore(2)

        async def task(task_id: int) -> int:
            async with semaphore_operation(semaphore, timeout=5.0):
                await asyncio.sleep(0.01)
                return task_id

        tasks = [task(i) for i in range(4)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 4
        assert set(results) == {0, 1, 2, 3}


class TestBoundedGather:
    """Test bounded_gather function."""

    @pytest.mark.asyncio
    async def test_bounded_gather_simple(self) -> None:
        """Test bounded_gather with simple coroutines."""
        semaphore = asyncio.Semaphore(2)

        async def return_one() -> int:
            return 1

        coros = [return_one() for _ in range(3)]

        results = await bounded_gather(coros, semaphore)

        assert len(results) == 3
        assert all(r == 1 for r in results)

    @pytest.mark.asyncio
    async def test_bounded_gather_preserves_order(self) -> None:
        """Test that bounded_gather preserves order of results."""
        semaphore = asyncio.Semaphore(2)

        async def return_value(i: int) -> int:
            return i

        coros = [return_value(i) for i in range(5)]

        results = await bounded_gather(coros, semaphore)

        assert results == [0, 1, 2, 3, 4]

    @pytest.mark.asyncio
    async def test_bounded_gather_with_exceptions(self) -> None:
        """Test bounded_gather with return_exceptions=True."""
        semaphore = asyncio.Semaphore(2)

        async def failing_coro() -> int:
            await asyncio.sleep(0.01)
            raise ValueError("Test error")

        async def success_coro() -> int:
            await asyncio.sleep(0.01)
            return 42

        coros = [failing_coro(), success_coro()]

        results = await bounded_gather(coros, semaphore, return_exceptions=True)

        assert len(results) == 2
        assert isinstance(results[0], ValueError)
        assert results[1] == 42


class TestBatchOperations:
    """Test batch_operations function."""

    @pytest.mark.asyncio
    async def test_batch_operations_simple(self) -> None:
        """Test batch_operations with simple items."""
        items = [1, 2, 3, 4, 5]

        async def process(item: int) -> int:
            await asyncio.sleep(0.001)
            return item * 2

        result = await batch_operations(items, operation=process, max_concurrent=2)

        assert isinstance(result, BatchResult)
        assert result.total_items == 5
        assert result.successful == 5
        assert result.failed == 0
        assert len(result.results) == 5
        assert sorted(result.results) == [2, 4, 6, 8, 10]

    @pytest.mark.asyncio
    async def test_batch_operations_with_errors(self) -> None:
        """Test batch_operations handles errors correctly."""
        items = [1, 2, 3]

        async def process(item: int) -> int:
            await asyncio.sleep(0.001)
            if item == 2:
                raise ValueError("Error on item 2")
            return item * 2

        result = await batch_operations(items, operation=process, max_concurrent=2)

        assert result.total_items == 3
        assert result.successful == 2
        assert result.failed == 1
        assert len(result.errors) == 1
        assert result.errors[0][0] == 1  # Index of failed item

    @pytest.mark.asyncio
    async def test_batch_operations_empty_list(self) -> None:
        """Test batch_operations with empty list."""
        result = await batch_operations([], operation=MagicMock(), max_concurrent=2)

        assert result.total_items == 0
        assert result.successful == 0
        assert result.failed == 0

    @pytest.mark.asyncio
    async def test_batch_operations_preserves_order(self) -> None:
        """Test that batch_operations preserves order."""
        items = [5, 3, 1, 4, 2]

        async def process(item: int) -> int:
            await asyncio.sleep(0.01)
            return item

        result = await batch_operations(items, operation=process, max_concurrent=10)

        # Results should be in the same order
        assert result.results == [5, 3, 1, 4, 2]

    @pytest.mark.asyncio
    async def test_batch_operations_duration_recorded(self) -> None:
        """Test that batch_operations records duration."""
        items = [1, 2]

        async def process(item: int) -> int:
            await asyncio.sleep(0.01)
            return item

        result = await batch_operations(items, operation=process, max_concurrent=2)

        assert result.duration_ms > 0
        assert result.duration_ms >= 10  # At least 10ms for the two 10ms sleeps

    @pytest.mark.asyncio
    async def test_batch_operations_with_timeout(self) -> None:
        """Test batch_operations with timeout on operations."""
        items = [1, 2]

        async def slow_process(item: int) -> int:
            await asyncio.sleep(0.1)
            return item

        # Should complete since no individual timeout
        result = await batch_operations(
            items, operation=slow_process, max_concurrent=2, timeout=1.0
        )

        assert result.successful == 2


class TestRateLimiter:
    """Test RateLimiter token bucket rate limiter."""

    @pytest.mark.asyncio
    async def test_rate_limiter_initial_state(self) -> None:
        """Test RateLimiter initial state."""
        limiter = RateLimiter(rate=10, period=1.0)

        assert limiter.rate == 10
        assert limiter.period == 1.0
        assert limiter.available_tokens == 10
        assert limiter.max_tokens == 10

    @pytest.mark.asyncio
    async def test_rate_limiter_custom_initial_tokens(self) -> None:
        """Test RateLimiter with custom initial tokens."""
        limiter = RateLimiter(rate=10, initial_tokens=5)

        assert limiter.available_tokens == 5

    @pytest.mark.asyncio
    async def test_rate_limiter_custom_max_tokens(self) -> None:
        """Test RateLimiter with custom max tokens."""
        limiter = RateLimiter(rate=10, max_tokens=20)

        assert limiter.max_tokens == 20

    @pytest.mark.asyncio
    async def test_rate_limiter_acquire_single(self) -> None:
        """Test acquiring a single token."""
        limiter = RateLimiter(rate=10, period=1.0)

        wait_time = await limiter.acquire(1)

        assert limiter.available_tokens == 9
        assert wait_time == 0.0

    @pytest.mark.asyncio
    async def test_rate_limiter_acquire_multiple(self) -> None:
        """Test acquiring multiple tokens at once."""
        limiter = RateLimiter(rate=10, period=1.0)

        wait_time = await limiter.acquire(5)

        assert limiter.available_tokens == 5
        assert wait_time == 0.0

    @pytest.mark.asyncio
    async def test_rate_limiter_exhausts_tokens(self) -> None:
        """Test rate limiter when tokens are exhausted."""
        limiter = RateLimiter(rate=2, period=1.0)

        # Use all tokens
        await limiter.acquire(2)
        # Token count may have refilled slightly, just verify it was reduced
        assert limiter.available_tokens < 2

        # Next acquire should require waiting
        start = time.monotonic()
        await limiter.acquire(1)
        elapsed = time.monotonic() - start

        # Should wait approximately 0.5 seconds (1 token / 2 tokens per second)
        assert elapsed >= 0.4  # Allow some tolerance

    @pytest.mark.asyncio
    async def test_rate_limiter_refills_over_time(self) -> None:
        """Test that rate limiter refills tokens over time."""
        limiter = RateLimiter(rate=10, period=1.0)

        # Use most tokens but leave room for refill check
        await limiter.acquire(8)
        initial_after_acquire = limiter.available_tokens

        # Wait for some refill
        await asyncio.sleep(0.3)

        # Should have more tokens now (refill happened)
        assert limiter.available_tokens >= initial_after_acquire

    @pytest.mark.asyncio
    async def test_rate_limiter_context_manager(self) -> None:
        """Test using rate limiter as context manager."""
        limiter = RateLimiter(rate=10, period=1.0)
        initial_tokens = limiter.available_tokens

        async with limiter:
            # Token should be acquired
            assert limiter.available_tokens == initial_tokens - 1

        # Token should remain consumed (context manager doesn't refill)
        assert limiter.available_tokens == initial_tokens - 1

    @pytest.mark.asyncio
    async def test_rate_limiter_max_tokens_limit(self) -> None:
        """Test that available tokens never exceed max_tokens."""
        limiter = RateLimiter(rate=10, period=0.1, max_tokens=5)

        # Acquire less than max
        await limiter.acquire(3)
        assert limiter.available_tokens == 2

        # Wait for refill which should respect max_tokens
        await asyncio.sleep(0.5)
        assert limiter.available_tokens <= limiter.max_tokens

    @pytest.mark.asyncio
    async def test_rate_limiter_burst_traffic(self) -> None:
        """Test rate limiter handles burst traffic correctly."""
        limiter = RateLimiter(rate=100, period=1.0, initial_tokens=100, max_tokens=100)

        # All tokens should be available initially
        assert limiter.available_tokens == 100

        # Acquire all tokens
        for _ in range(100):
            await limiter.acquire(1)

        # Tokens should be mostly consumed (allow for slight refill during test)
        assert limiter.available_tokens <= 5


# =============================================================================
# Exports
# =============================================================================


__all__ = [
    "TestConcurrentImports",
    "TestSemaphoreOperation",
    "TestBoundedGather",
    "TestBatchOperations",
    "TestRateLimiter",
]
