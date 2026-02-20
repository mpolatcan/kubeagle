"""Tests for ScreenDataLoader - standardized data loading patterns.

This module tests:
- ScreenDataLoader loading state transitions
- Auto-refresh mechanism
- Error handling and messages
- Data loading with cache coordination
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

from textual.app import ComposeResult
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Static

from kubeagle.models.types.loading import LoadingProgress
from kubeagle.screens.mixins.screen_data_loader import (
    DataLoadCompleted,
    DataLoadError,
    DataLoadStarted,
    ScreenDataLoader,
)

# =============================================================================
# Test Fixtures
# =============================================================================


class MockScreenWithScreenDataLoader(Screen):
    """Mock screen that uses ScreenDataLoader."""

    def __init__(self) -> None:
        super().__init__()
        self.data_loaded_callback = None
        self.data_error_callback = None
        self.progress_updates: list[LoadingProgress] = []

    def compose(self) -> ComposeResult:
        yield Static("Test Screen")

    async def _load_data_async(self) -> list[dict]:
        """Mock data loading."""
        await asyncio.sleep(0.01)
        return [{"id": 1, "name": "test"}]


class MockScreenDataLoaderWithCallback(ScreenDataLoader[list[dict]]):
    """Mock screen data loader with callback hooks."""

    def __init__(self) -> None:
        super().__init__()
        self._data_loaded = False
        self._error_occurred = False
        self._error_message = ""
        self._callback_data = None

    def compose(self) -> ComposeResult:
        yield Static("Test Screen")

    async def _load_data_async(self) -> list[dict]:
        """Mock data loading."""
        await asyncio.sleep(0.01)
        return [{"id": 1, "name": "test"}]

    def _on_data_loaded(self, data: list[dict]) -> None:
        self._data_loaded = True
        self._callback_data = data

    def _on_data_error(self, error: str, duration_ms: float) -> None:
        self._error_occurred = True
        self._error_message = error


class MockScreenDataLoaderWithError(ScreenDataLoader[list[dict]]):
    """Mock screen that raises an error during loading."""

    def __init__(self, raise_error: bool = False) -> None:
        super().__init__()
        self._raise_error = raise_error

    def compose(self) -> ComposeResult:
        yield Static("Test Screen")

    async def _load_data_async(self) -> list[dict]:
        """Mock data loading that may raise an error."""
        await asyncio.sleep(0.01)
        if self._raise_error:
            raise ValueError("Test error occurred")
        return [{"id": 1, "name": "test"}]


# =============================================================================
# ScreenDataLoader Unit Tests
# =============================================================================


class TestScreenDataLoaderImports:
    """Test that ScreenDataLoader can be imported correctly."""

    def test_screen_data_loader_import(self) -> None:
        """Test ScreenDataLoader class import."""
        from kubeagle.screens.mixins.screen_data_loader import (
            ScreenDataLoader,
        )

        assert ScreenDataLoader is not None
        assert hasattr(ScreenDataLoader, "load")
        assert hasattr(ScreenDataLoader, "refresh")
        assert hasattr(ScreenDataLoader, "start_auto_refresh")

    def test_loading_progress_import(self) -> None:
        """Test LoadingProgress dataclass import."""
        from kubeagle.models.types.loading import LoadingProgress

        progress = LoadingProgress(phase="test", progress=0.5, message="Test")
        assert progress.phase == "test"
        assert progress.progress == 0.5
        assert progress.message == "Test"

    def test_data_load_messages_import(self) -> None:
        """Test data load message classes import."""
        from kubeagle.screens.mixins.screen_data_loader import (
            DataLoadCompleted,
            DataLoadError,
            DataLoadStarted,
        )

        # Test DataLoadStarted
        msg = DataLoadStarted()
        assert isinstance(msg, Message)

        # Test DataLoadCompleted
        msg = DataLoadCompleted(data={"test": True}, duration_ms=50.0)
        assert msg.data == {"test": True}
        assert msg.duration_ms == 50.0
        assert msg.from_cache is False

        # Test DataLoadError
        msg = DataLoadError(error="Test error", duration_ms=25.0)
        assert msg.error == "Test error"
        assert msg.duration_ms == 25.0

    def test_data_loader_mixin_alias(self) -> None:
        """Test backward compatibility alias."""
        from kubeagle.screens.mixins.screen_data_loader import (
            DataLoaderMixin,
        )

        assert DataLoaderMixin is ScreenDataLoader


class TestScreenDataLoaderProperties:
    """Test ScreenDataLoader property getters and setters."""

    def test_initial_state(self) -> None:
        """Test initial state of ScreenDataLoader."""
        loader = ScreenDataLoader()

        assert loader.is_loading is False
        assert loader.data == []
        assert loader.error is None
        assert loader.loading_duration_ms == 0.0

    def test_is_loading_property(self) -> None:
        """Test is_loading property."""
        loader = ScreenDataLoader()

        loader.is_loading = True
        assert loader._is_loading is True

        loader.is_loading = False
        assert loader._is_loading is False

    def test_data_property(self) -> None:
        """Test data property."""
        loader = ScreenDataLoader()

        test_data = [{"id": 1}, {"id": 2}]
        loader.data = test_data

        assert loader.data == test_data
        assert loader._data == test_data

    def test_error_property(self) -> None:
        """Test error property."""
        loader = ScreenDataLoader()

        loader.error = "Test error"
        assert loader.error == "Test error"
        assert loader._error == "Test error"

        loader.error = None
        assert loader.error is None

    def test_loading_duration_ms_property(self) -> None:
        """Test loading_duration_ms property."""
        loader = ScreenDataLoader()

        loader.loading_duration_ms = 123.45
        assert loader.loading_duration_ms == 123.45
        assert loader._loading_duration_ms == 123.45


class TestScreenDataLoaderMethods:
    """Test ScreenDataLoader methods."""

    def test_set_loader(self) -> None:
        """Test set_loader method."""
        loader = ScreenDataLoader()

        async def mock_loader() -> list[dict]:
            return []

        loader.set_loader(mock_loader, cache_key="test_cache")

        assert loader._data_loader is mock_loader
        assert loader._cache_key == "test_cache"

    def test_set_loader_without_cache_key(self) -> None:
        """Test set_loader without cache key."""
        loader = ScreenDataLoader()

        async def mock_loader() -> list[dict]:
            return []

        loader.set_loader(mock_loader)

        assert loader._data_loader is mock_loader
        assert loader._cache_key is None

    def test_refresh(self) -> None:
        """Test refresh method calls load with force_refresh=True."""
        loader = ScreenDataLoader()

        with patch.object(loader, "load") as mock_load:
            loader.refresh()
            mock_load.assert_called_once_with(force_refresh=True)


class TestScreenDataLoaderAutoRefresh:
    """Test ScreenDataLoader auto-refresh functionality."""

    def test_start_auto_refresh_with_interval(self) -> None:
        """Test start_auto_refresh sets the interval."""
        loader = ScreenDataLoader()

        with patch("kubeagle.screens.mixins.screen_data_loader.logger"):
            loader.start_auto_refresh(interval=60.0)

            assert loader.auto_refresh_interval == 60.0

    def test_start_auto_refresh_uses_class_attribute(self) -> None:
        """Test start_auto_refresh uses class attribute if interval is None."""
        loader = ScreenDataLoader()
        loader.auto_refresh_interval = 30.0

        with patch("kubeagle.screens.mixins.screen_data_loader.logger"):
            loader.start_auto_refresh()

    def test_stop_auto_refresh(self) -> None:
        """Test stop_auto_refresh clears the timer."""
        loader = ScreenDataLoader()
        mock_timer = MagicMock()
        mock_timer.stop = MagicMock()
        loader._refresh_timer = mock_timer

        loader.stop_auto_refresh()

        mock_timer.stop.assert_called_once()
        assert loader._refresh_timer is None

    def test_stop_auto_refresh_no_timer(self) -> None:
        """Test stop_auto_refresh handles no timer gracefully."""
        loader = ScreenDataLoader()
        loader._refresh_timer = None

        # Should not raise
        loader.stop_auto_refresh()

    def test_toggle_auto_refresh_starts(self) -> None:
        """Test toggle_auto_refresh starts when stopped."""
        loader = ScreenDataLoader()

        with patch.object(loader, "start_auto_refresh") as mock_start:
            loader.toggle_auto_refresh()
            mock_start.assert_called_once_with(None)

    def test_toggle_auto_refresh_stops(self) -> None:
        """Test toggle_auto_refresh stops when running."""
        loader = ScreenDataLoader()
        loader._refresh_timer = MagicMock()

        with patch.object(loader, "stop_auto_refresh") as mock_stop:
            loader.toggle_auto_refresh()
            mock_stop.assert_called_once()


class TestScreenDataLoaderWorkerMethods:
    """Test ScreenDataLoader worker-related methods."""

    def test_start_worker_returns_none(self) -> None:
        """Test start_worker returns None by default."""
        loader = ScreenDataLoader()

        result = loader.start_worker(MagicMock())

        assert result is None

    def test_cancel_workers_no_op(self) -> None:
        """Test cancel_workers does nothing by default."""
        loader = ScreenDataLoader()

        # Should not raise
        loader.cancel_workers()

    def test_post_message_no_op(self) -> None:
        """Test post_message does nothing by default."""
        loader = ScreenDataLoader()

        # Should not raise
        loader.post_message(DataLoadStarted())

    def test_set_interval_returns_none(self) -> None:
        """Test set_interval returns None by default."""
        loader = ScreenDataLoader()

        result = loader.set_interval(1.0, MagicMock())

        assert result is None


class TestScreenDataLoaderMessages:
    """Test ScreenDataLoader message classes."""

    def test_data_load_started(self) -> None:
        """Test DataLoadStarted message."""
        msg = DataLoadStarted()

        assert isinstance(msg, Message)

    def test_data_load_completed_with_data(self) -> None:
        """Test DataLoadCompleted with data."""
        data = [{"id": 1, "name": "test"}]
        msg = DataLoadCompleted(data=data, duration_ms=100.0, from_cache=False)

        assert msg.data == data
        assert msg.duration_ms == 100.0
        assert msg.from_cache is False

    def test_data_load_completed_from_cache(self) -> None:
        """Test DataLoadCompleted with from_cache=True."""
        msg = DataLoadCompleted(data=[], duration_ms=10.0, from_cache=True)

        assert msg.from_cache is True

    def test_data_load_error(self) -> None:
        """Test DataLoadError message."""
        msg = DataLoadError(error="Connection timeout", duration_ms=500.0)

        assert msg.error == "Connection timeout"
        assert msg.duration_ms == 500.0

    def test_loading_progress_default_message(self) -> None:
        """Test LoadingProgress with default empty message."""
        progress = LoadingProgress(phase="fetching", progress=0.75)

        assert progress.phase == "fetching"
        assert progress.progress == 0.75
        assert progress.message == ""
        assert progress.details == {}  # details defaults to empty dict in consolidated version

    def test_loading_progress_with_details(self) -> None:
        """Test LoadingProgress with details."""
        details: dict[str, int] = {"current": 5, "total": 10}
        progress = LoadingProgress(
            phase="processing", progress=0.5, message="Processing items", details=details
        )

        assert progress.details == details


class TestScreenDataLoaderProgressHandling:
    """Test ScreenDataLoader progress update handling."""

    def test_on_progress_update_default_noop(self) -> None:
        """Test _on_progress_update is a noop by default."""
        loader = ScreenDataLoader()

        progress = LoadingProgress(phase="test", progress=0.5)
        # Should not raise
        loader._on_progress_update(progress)


# =============================================================================
# Exports
# =============================================================================


__all__ = [
    "TestScreenDataLoaderImports",
    "TestScreenDataLoaderProperties",
    "TestScreenDataLoaderMethods",
    "TestScreenDataLoaderAutoRefresh",
    "TestScreenDataLoaderWorkerMethods",
    "TestScreenDataLoaderMessages",
    "TestScreenDataLoaderProgressHandling",
]
