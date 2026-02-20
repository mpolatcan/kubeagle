"""Tests for base controller module."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from kubeagle.controllers.base.base_controller import (
    AsyncControllerMixin,
    BaseController,
    WorkerResult,
)


class TestWorkerResult:
    """Tests for WorkerResult dataclass."""

    def test_worker_result_success(self) -> None:
        """Test successful worker result."""
        result = WorkerResult(success=True, data={"key": "value"}, duration_ms=100.0)
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None
        assert result.duration_ms == 100.0

    def test_worker_result_error(self) -> None:
        """Test error worker result."""
        result = WorkerResult(success=False, error="Something went wrong", duration_ms=50.0)
        assert result.success is False
        assert result.data is None
        assert result.error == "Something went wrong"
        assert result.duration_ms == 50.0

    def test_worker_result_defaults(self) -> None:
        """Test WorkerResult default values."""
        result = WorkerResult(success=True)
        assert result.data is None
        assert result.error is None
        assert result.duration_ms == 0.0


class TestAsyncControllerMixin:
    """Tests for AsyncControllerMixin class."""

    @pytest.fixture
    def mixin(self) -> AsyncControllerMixin:
        """Create mixin instance for testing."""
        return AsyncControllerMixin()

    def test_default_semaphore_property(self, mixin: AsyncControllerMixin) -> None:
        """Test default semaphore property."""
        semaphore = mixin.default_semaphore
        assert isinstance(semaphore, asyncio.Semaphore)
        assert semaphore._value == 8  # Default value is 8

    def test_create_semaphore(self, mixin: AsyncControllerMixin) -> None:
        """Test semaphore creation."""
        semaphore = mixin.create_semaphore(4)
        assert isinstance(semaphore, asyncio.Semaphore)
        assert semaphore._value == 4

    @pytest.mark.asyncio
    async def test_bounded_operation_success(self, mixin: AsyncControllerMixin) -> None:
        """Test bounded operation with successful acquire."""
        semaphore = mixin.create_semaphore(1)
        async with mixin.bounded_operation(semaphore):
            result = "operation completed"
        assert result == "operation completed"

    @pytest.mark.asyncio
    async def test_bounded_operation_with_timeout(self, mixin: AsyncControllerMixin) -> None:
        """Test bounded operation with timeout."""
        semaphore = mixin.create_semaphore(1)
        # Acquire the semaphore first so the next acquire will block
        await semaphore.acquire()
        # This should timeout
        with pytest.raises(asyncio.TimeoutError):
            async with mixin.bounded_operation(semaphore, timeout=0.1):
                pass

    @pytest.mark.asyncio
    async def test_run_with_worker_success(self, mixin: AsyncControllerMixin) -> None:
        """Test run_with_worker with successful execution."""
        async def sample_awaitable() -> str:
            return "result"

        result = await mixin.run_with_worker(sample_awaitable())
        assert result.success is True
        assert result.data == "result"
        assert result.error is None
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_run_with_worker_timeout(self, mixin: AsyncControllerMixin) -> None:
        """Test run_with_worker with timeout."""
        async def slow_awaitable() -> str:
            await asyncio.sleep(10)
            return "result"

        result = await mixin.run_with_worker(slow_awaitable(), timeout=0.1)
        assert result.success is False
        assert result.data is None
        assert result.error is not None and "timed out" in result.error
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_run_with_worker_exception(self, mixin: AsyncControllerMixin) -> None:
        """Test run_with_worker with exception."""

        async def failing_awaitable() -> str:
            raise ValueError("Test error")

        result = await mixin.run_with_worker(failing_awaitable())
        assert result.success is False
        assert result.data is None
        assert result.error == "Test error"

    def test_check_cancellation_no_worker(self, mixin: AsyncControllerMixin) -> None:
        """Test check_cancellation when no worker is running raises NoActiveWorker.

        The implementation calls get_current_worker() which raises
        NoActiveWorker when there is no active Textual worker context.
        """
        from textual.worker import NoActiveWorker

        with pytest.raises(NoActiveWorker):
            mixin.check_cancellation()

    def test_check_cancellation_with_mocked_worker(self, mixin: AsyncControllerMixin) -> None:
        """Test check_cancellation with mocked worker."""
        mock_worker = MagicMock()
        mock_worker.is_cancelled = True

        with patch("kubeagle.controllers.base.base_controller.get_current_worker", return_value=mock_worker):
            result = mixin.check_cancellation()
            assert result is True

        mock_worker.is_cancelled = False
        with patch("kubeagle.controllers.base.base_controller.get_current_worker", return_value=mock_worker):
            result = mixin.check_cancellation()
            assert result is False


class TestBaseController:
    """Tests for BaseController abstract class."""

    def test_base_controller_is_abstract(self) -> None:
        """Test that BaseController is abstract and cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseController()

    def test_base_controller_inherits_from_async_mixin(self) -> None:
        """Test that BaseController inherits from AsyncControllerMixin."""

        class ConcreteController(BaseController):
            async def check_connection(self) -> bool:
                return True

            async def fetch_all(self) -> dict:
                return {}

        controller = ConcreteController()
        assert isinstance(controller, AsyncControllerMixin)
        assert hasattr(controller, "default_semaphore")
        assert hasattr(controller, "run_with_worker")
        assert hasattr(controller, "bounded_operation")
