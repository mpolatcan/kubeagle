"""Tests for pod fetcher."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from kubeagle.constants.timeouts import CLUSTER_REQUEST_TIMEOUT
from kubeagle.controllers.cluster.fetchers.pod_fetcher import (
    PodFetcher,
)


class TestPodFetcher:
    """Tests for PodFetcher class."""

    @pytest.fixture
    def mock_run_kubectl(self) -> AsyncMock:
        """Create mock run_kubectl function."""
        return AsyncMock()

    def test_fetcher_init(self, mock_run_kubectl: AsyncMock) -> None:
        """Test PodFetcher initialization with run_kubectl_func."""
        fetcher = PodFetcher(run_kubectl_func=mock_run_kubectl)
        assert fetcher._run_kubectl is mock_run_kubectl

    def test_fetcher_init_default_context(self, mock_run_kubectl: AsyncMock) -> None:
        """Test PodFetcher initialization stores the callable."""
        fetcher = PodFetcher(mock_run_kubectl)
        assert fetcher._run_kubectl is mock_run_kubectl

    @pytest.mark.asyncio
    async def test_fetch_pods_uses_chunked_query(
        self,
        mock_run_kubectl: AsyncMock,
    ) -> None:
        """fetch_pods should request chunked all-namespaces pod JSON."""
        mock_run_kubectl.return_value = '{"items": [{"metadata": {"name": "pod-a"}}]}'
        fetcher = PodFetcher(mock_run_kubectl)

        pods = await fetcher.fetch_pods()

        assert len(pods) == 1
        called_args = mock_run_kubectl.await_args_list[0].args[0]
        assert "--chunk-size=200" in called_args
        assert f"--request-timeout={CLUSTER_REQUEST_TIMEOUT}" in called_args
        assert "--field-selector=status.phase=Running" not in called_args

    @pytest.mark.asyncio
    async def test_fetch_pods_retries_timeout_with_default_timeout(
        self,
        mock_run_kubectl: AsyncMock,
    ) -> None:
        """Short custom timeout should retry with default cluster timeout."""
        mock_run_kubectl.side_effect = [
            RuntimeError("request timed out"),
            '{"items": [{"metadata": {"name": "pod-a"}}]}',
        ]
        fetcher = PodFetcher(mock_run_kubectl)

        pods = await fetcher.fetch_pods(request_timeout="8s")

        assert len(pods) == 1
        assert mock_run_kubectl.await_count == 2
        first_args = mock_run_kubectl.await_args_list[0].args[0]
        second_args = mock_run_kubectl.await_args_list[1].args[0]
        assert "--request-timeout=8s" in first_args
        assert f"--request-timeout={CLUSTER_REQUEST_TIMEOUT}" in second_args

    @pytest.mark.asyncio
    async def test_fetch_pods_falls_back_to_running_only_query(
        self,
        mock_run_kubectl: AsyncMock,
    ) -> None:
        """Timeout retries should end with running-only fallback query."""
        mock_run_kubectl.side_effect = [
            RuntimeError("i/o timeout"),
            RuntimeError("deadline exceeded"),
            '{"items": [{"metadata": {"name": "pod-running"}}]}',
        ]
        fetcher = PodFetcher(mock_run_kubectl)

        pods = await fetcher.fetch_pods(request_timeout="8s")

        assert len(pods) == 1
        assert mock_run_kubectl.await_count == 3
        final_args = mock_run_kubectl.await_args_list[2].args[0]
        assert "--field-selector=status.phase=Running" in final_args
        assert "--request-timeout=45s" in final_args

    @pytest.mark.asyncio
    async def test_fetch_pods_raises_non_timeout_errors(
        self,
        mock_run_kubectl: AsyncMock,
    ) -> None:
        """Non-timeout failures should be raised without retries."""
        mock_run_kubectl.side_effect = RuntimeError("forbidden")
        fetcher = PodFetcher(mock_run_kubectl)

        with pytest.raises(RuntimeError, match="forbidden"):
            await fetcher.fetch_pods()

        assert mock_run_kubectl.await_count == 1

    @pytest.mark.asyncio
    async def test_fetch_pods_for_namespace_uses_namespace_scope(
        self,
        mock_run_kubectl: AsyncMock,
    ) -> None:
        """Namespace-scoped fetch should use -n namespace instead of -A."""
        mock_run_kubectl.return_value = '{"items": [{"metadata": {"name": "pod-a"}}]}'
        fetcher = PodFetcher(mock_run_kubectl)

        pods = await fetcher.fetch_pods_for_namespace("payments")

        assert len(pods) == 1
        called_args = mock_run_kubectl.await_args_list[0].args[0]
        assert "-A" not in called_args
        assert "-n" in called_args
        ns_index = called_args.index("-n")
        assert called_args[ns_index + 1] == "payments"
