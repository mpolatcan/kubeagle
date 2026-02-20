"""Base controller with async worker-friendly patterns for KubEagle TUI.

This module provides the foundation for background data loading using Textual Workers,
ensuring the UI remains responsive during kubectl/helm operations.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, TypeVar

from textual.worker import get_current_worker

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class WorkerResult:
    """Result wrapper for worker operations."""

    success: bool
    data: Any | None = None
    error: str | None = None
    duration_ms: float = 0.0


class AsyncControllerMixin:
    """Mixin providing worker-friendly async patterns for controllers.

    This mixin enables controllers to be used with Textual Workers for
    background data loading without blocking the UI.
    """

    def __init__(self) -> None:
        """Initialize the async controller mixin."""
        self._load_start_time: float | None = None
        # Default semaphore for concurrent operations (8 concurrent by default)
        self._default_semaphore = asyncio.Semaphore(8)

    # =========================================================================
    # Semaphore Utilities
    # =========================================================================

    @property
    def default_semaphore(self) -> asyncio.Semaphore:
        """Get the default semaphore for concurrent operations."""
        return self._default_semaphore

    def create_semaphore(self, max_concurrent: int) -> asyncio.Semaphore:
        """Create a new semaphore for controlling concurrent operations.

        Args:
            max_concurrent: Maximum number of concurrent operations

        Returns:
            New semaphore instance
        """
        return asyncio.Semaphore(max_concurrent)

    @asynccontextmanager
    async def bounded_operation(
        self,
        semaphore: asyncio.Semaphore | None = None,
        *,
        timeout: float | None = None,
    ):
        """Context manager for semaphore-controlled operations.

        Args:
            semaphore: Semaphore to use (defaults to default_semaphore)
            timeout: Optional timeout for acquiring the semaphore

        Usage:
            async with self.bounded_operation():
                await fetch_data()
        """
        sem = semaphore or self._default_semaphore

        acquired = False
        try:
            if timeout:
                acquired = await asyncio.wait_for(sem.acquire(), timeout=timeout)
            else:
                await sem.acquire()
                acquired = True
            yield
        finally:
            if acquired:
                sem.release()

    async def run_with_worker(
        self,
        awaitable: Awaitable[T],
        timeout: float | None = None,
    ) -> WorkerResult:
        """Run an awaitable with timeout support.

        Args:
            awaitable: The awaitable to execute
            timeout: Optional timeout in seconds

        Returns:
            WorkerResult with success status and data/error
        """
        start_time = datetime.now().timestamp()

        try:
            if timeout:
                data = await asyncio.wait_for(awaitable, timeout=timeout)
            else:
                data = await awaitable

            duration_ms = (datetime.now().timestamp() - start_time) * 1000
            return WorkerResult(
                success=True,
                data=data,
                duration_ms=duration_ms,
            )

        except asyncio.TimeoutError:
            duration_ms = (datetime.now().timestamp() - start_time) * 1000
            logger.warning(f"Operation timed out after {timeout}s")
            return WorkerResult(
                success=False,
                error=f"Operation timed out after {timeout}s",
                duration_ms=duration_ms,
            )
        except asyncio.CancelledError:
            duration_ms = (datetime.now().timestamp() - start_time) * 1000
            return WorkerResult(
                success=False,
                error="Operation was cancelled",
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = (datetime.now().timestamp() - start_time) * 1000
            logger.exception(f"Operation failed: {e}")
            return WorkerResult(
                success=False,
                error=str(e),
                duration_ms=duration_ms,
            )

    def check_cancellation(self) -> bool:
        """Check if the current worker has been cancelled.

        Call this method periodically during long-running operations
        to support graceful cancellation.

        Returns:
            True if worker is cancelled, False otherwise
        """
        worker = get_current_worker()
        if worker:
            return worker.is_cancelled
        return False


class BaseController(AsyncControllerMixin, ABC):
    """Base controller class with worker-friendly patterns.

    Subclasses should implement the abstract methods to provide
    specific data fetching functionality.
    """

    @abstractmethod
    async def check_connection(self) -> bool:
        """Check if the data source is available.

        Returns:
            True if connection is available, False otherwise
        """
        ...

    @abstractmethod
    async def fetch_all(self) -> dict[str, Any]:
        """Fetch all data from the source.

        Returns:
            Dictionary containing all fetched data
        """
        ...
