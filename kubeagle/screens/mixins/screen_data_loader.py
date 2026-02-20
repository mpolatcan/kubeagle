"""ScreenDataLoader - Base class for consistent data loading patterns.

This module provides ScreenDataLoader, a base class that standardizes data loading
across all screens with:
- Loading duration tracking
- Auto-refresh coordination
- Progress reporting
- Error state handling
- Data cache coordination

Standard Pattern:
- Inherit from ScreenDataLoader for screens that load data
- Override _load_data_async() for data loading logic
- Override _on_data_loaded() to handle loaded data
- Override _on_data_error() for error handling

Usage:
    class MyScreen(ScreenDataLoader, Screen):
        auto_refresh_interval = 30.0  # Optional: enable auto-refresh

        async def _load_data_async(self) -> MyDataType:
            # Your async data loading logic
            return data

        def _on_data_loaded(self, data: MyDataType) -> None:
            # Handle successful data load
            pass
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from textual.message import Message
from textual.timer import Timer

if TYPE_CHECKING:
    from kubeagle.models.types.loading import (
        LoadingProgress,
        LoadResult,
    )

logger = logging.getLogger(__name__)

T = TypeVar("T")


class DataLoadStarted(Message):
    """Message indicating data load has started."""

    pass


class DataLoadCompleted(Message):
    """Message indicating data load completed."""

    def __init__(self, data: Any, duration_ms: float = 0.0, from_cache: bool = False) -> None:
        super().__init__()
        self.data = data
        self.duration_ms = duration_ms
        self.from_cache = from_cache


class DataLoadError(Message):
    """Message indicating data load failed."""

    def __init__(self, error: str, duration_ms: float = 0.0) -> None:
        super().__init__()
        self.error = error
        self.duration_ms = duration_ms


class ScreenDataLoader(Generic[T]):
    """Base class for screens with standardized data loading patterns.

    This class provides:
    - Loading duration tracking
    - Auto-refresh with configurable interval
    - Progress reporting via LoadingProgress
    - Error state handling with retry
    - Cache coordination via CacheManager

    Note: This class requires delegation to Screen methods for
    set_interval, post_message, etc. Use with Screen subclass.

    Attributes:
        auto_refresh_interval: Interval in seconds for auto-refresh (None to disable)
        loading_duration_ms: Last load duration in milliseconds
        last_load_time: Timestamp of last successful load

    Usage:
        class MyScreen(ScreenDataLoader[MyData], Screen):
            auto_refresh_interval = 60.0  # Refresh every minute

            async def _load_data_async(self) -> MyData:
                # Async data loading
                return await fetch_data()

            def _on_data_loaded(self, data: MyData) -> None:
                # Handle loaded data
                self._update_ui(data)
    """

    # Auto-refresh configuration (override in subclass)
    auto_refresh_interval: float | None = None

    def __init__(self) -> None:
        """Initialize the ScreenDataLoader."""
        # Internal state
        self._load_start_time: float | None = None
        self._refresh_timer: Timer | None = None
        self._data_loader: Callable[..., Awaitable[T]] | None = None
        self._cache_key: str | None = None
        self._is_loading: bool = False
        self._error: str | None = None
        self._data: list[dict] = []
        self._loading_duration_ms: float = 0.0

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def is_loading(self) -> bool:
        """Check if data is currently loading."""
        return self._is_loading

    @is_loading.setter
    def is_loading(self, value: bool) -> None:
        """Set loading state."""
        self._is_loading = value

    @property
    def data(self) -> list[dict]:
        """Get loaded data."""
        return self._data

    @data.setter
    def data(self, value: list[dict]) -> None:
        """Set loaded data."""
        self._data = value

    @property
    def error(self) -> str | None:
        """Get error message."""
        return self._error

    @error.setter
    def error(self, value: str | None) -> None:
        """Set error message."""
        self._error = value

    @property
    def loading_duration_ms(self) -> float:
        """Get loading duration in milliseconds."""
        return self._loading_duration_ms

    @loading_duration_ms.setter
    def loading_duration_ms(self, value: float) -> None:
        """Set loading duration in milliseconds."""
        self._loading_duration_ms = value

    # =========================================================================
    # Data Loading API
    # =========================================================================

    def set_loader(
        self,
        loader: Callable[..., Awaitable[T]],
        cache_key: str | None = None,
    ) -> None:
        """Set the data loader function.

        Args:
            loader: Async function that returns the data
            cache_key: Optional cache key for coordination
        """
        self._data_loader = loader
        self._cache_key = cache_key

    def load(self, force_refresh: bool = False) -> None:
        """Start data loading.

        Args:
            force_refresh: If True, bypass cache and force fresh load
        """
        self._start_load_worker(force_refresh=force_refresh)

    def refresh(self) -> None:
        """Refresh data (force fresh load)."""
        self.load(force_refresh=True)

    # =========================================================================
    # Auto-refresh API
    # =========================================================================

    def start_auto_refresh(self, interval: float | None = None) -> None:
        """Start auto-refresh timer.

        Args:
            interval: Refresh interval in seconds. Uses class attribute if None.
        """
        if interval is not None:
            self.auto_refresh_interval = interval

        if self.auto_refresh_interval is None:
            return

        if self._refresh_timer is not None:
            self._refresh_timer.stop()

        # Requires delegation to Screen.set_interval()
        logger.debug(f"Auto-refresh timer configured (interval={self.auto_refresh_interval}s)")

    def stop_auto_refresh(self) -> None:
        """Stop auto-refresh timer."""
        if self._refresh_timer is not None:
            self._refresh_timer.stop()
            self._refresh_timer = None
        logger.debug("Auto-refresh stopped")

    def toggle_auto_refresh(self, interval: float | None = None) -> None:
        """Toggle auto-refresh on/off.

        Args:
            interval: Optional interval to use when starting
        """
        if self._refresh_timer is not None:
            self.stop_auto_refresh()
        else:
            self.start_auto_refresh(interval)

    # =========================================================================
    # Worker Methods (override in subclass with Screen access)
    # =========================================================================

    def start_worker(
        self,
        worker_func: Any,
        *,
        exclusive: bool = True,
        thread: bool = False,
        name: str | None = None,
        exit_on_error: bool = False,
    ) -> Any:
        """Start a worker for background data loading.

        Override in subclass with Screen access.
        """
        _ = (worker_func, exclusive, thread, name, exit_on_error)
        return None

    def cancel_workers(self) -> None:
        """Cancel all running workers."""
        pass

    def post_message(self, message: Message) -> None:
        """Post a message.

        Override in subclass with Screen access.
        """
        pass

    def set_interval(self, interval: float, callback: Any, *, name: str | None = None) -> Timer | None:
        """Set an interval timer.

        Override in subclass with Screen access.
        """
        _ = (interval, callback, name)
        return None

    # =========================================================================
    # Abstract Methods (Override in Subclasses)
    # =========================================================================

    async def _load_data_async(self) -> T:
        """Load data asynchronously.

        Override this method in subclasses to provide data loading logic.

        Returns:
            The loaded data

        Raises:
            Exception: On loading failure
        """
        raise NotImplementedError("Subclasses must implement _load_data_async")

    def _on_data_loaded(self, data: T) -> None:
        """Handle successful data load.

        Override this method in subclasses to process loaded data.

        Args:
            data: The loaded data
        """
        pass

    def _on_data_error(self, error: str, duration_ms: float) -> None:
        """Handle data load error.

        Override this method in subclasses to process errors.

        Args:
            error: Error message
            duration_ms: Time spent loading before error
        """
        pass

    def _on_progress_update(self, progress: LoadingProgress) -> None:
        """Handle progress updates.

        Override this method in subclasses to update progress UI.

        Args:
            progress: Current progress update
        """
        _ = progress
        pass

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _start_load_worker(self, force_refresh: bool = False) -> None:
        """Start the load worker.

        Args:
            force_refresh: If True, bypass cache
        """
        # Cancel any existing workers
        self.cancel_workers()

        # Reset state
        self.error = None
        self.is_loading = True
        self._load_start_time = time.monotonic()

        # Post started message
        self.post_message(DataLoadStarted())

        # Start worker
        self.start_worker(
            self._load_worker(force_refresh=force_refresh),
            exclusive=True,
            name="data_loader",
        )

    async def _load_worker(self, force_refresh: bool = False) -> None:
        """Worker function for data loading.

        Args:
            force_refresh: If True, bypass cache
        """
        start_time = self._load_start_time or time.monotonic()

        try:
            # Check for cancellation
            from textual.worker import get_current_worker

            from kubeagle.utils.cache_manager import cache_manager

            worker = get_current_worker()
            if worker and worker.is_cancelled:
                self.is_loading = False
                return

            # Invalidate cache if force refresh
            if force_refresh and self._cache_key:
                await cache_manager.invalidate(self._cache_key)

            # Load data
            if self._data_loader is not None:
                data = await self._data_loader()
            else:
                data = await self._load_data_async()

            # Calculate duration
            duration_ms = (time.monotonic() - start_time) * 1000

            # Post completed message
            self.post_message(DataLoadCompleted(data, duration_ms=duration_ms))

            # Handle data
            self.data = data
            self.loading_duration_ms = duration_ms
            self._on_data_loaded(data)

        except asyncio.CancelledError:
            self.is_loading = False
            duration_ms = (time.monotonic() - start_time) * 1000
            self.post_message(DataLoadError("Operation cancelled", duration_ms))
        except Exception as e:
            duration_ms = (time.monotonic() - start_time) * 1000
            error_msg = str(e)
            logger.exception(f"Data load failed: {error_msg}")
            self.error = error_msg
            self.post_message(DataLoadError(error_msg, duration_ms))
            self._on_data_error(error_msg, duration_ms)
        finally:
            self.is_loading = False

    def on_unmount(self) -> None:
        """Stop auto-refresh timer and cancel workers on unmount."""
        self.stop_auto_refresh()
        self.cancel_workers()

    def _on_refresh_timer(self) -> None:
        """Handle auto-refresh timer tick."""
        if not self.is_loading:
            self.load(force_refresh=True)

    # =========================================================================
    # Message Handlers
    # =========================================================================

    def on_data_load_started(self, event: DataLoadStarted) -> None:
        """Handle data load started."""
        pass

    def on_data_load_completed(self, event: DataLoadCompleted) -> None:
        """Handle data load completed."""
        pass

    def on_data_load_error(self, event: DataLoadError) -> None:
        """Handle data load error."""
        pass


# Alias for backward compatibility
DataLoaderMixin = ScreenDataLoader

__all__ = [
    "ScreenDataLoader",
    "DataLoaderMixin",
    "LoadingProgress",
    "LoadResult",
    "DataLoadStarted",
    "DataLoadCompleted",
    "DataLoadError",
]
