"""Tests for node fetcher."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from kubeagle.controllers.cluster.fetchers.node_fetcher import (
    NodeFetcher,
)


class TestNodeFetcher:
    """Tests for NodeFetcher class."""

    @pytest.fixture
    def mock_run_kubectl(self) -> AsyncMock:
        """Create mock run_kubectl function."""
        return AsyncMock()

    def test_fetcher_init(self, mock_run_kubectl: AsyncMock) -> None:
        """Test NodeFetcher initialization with run_kubectl_func."""
        fetcher = NodeFetcher(run_kubectl_func=mock_run_kubectl)
        assert fetcher._run_kubectl is mock_run_kubectl

    def test_fetcher_init_default_context(self, mock_run_kubectl: AsyncMock) -> None:
        """Test NodeFetcher initialization stores the callable."""
        fetcher = NodeFetcher(mock_run_kubectl)
        assert fetcher._run_kubectl is mock_run_kubectl

    @pytest.mark.asyncio
    async def test_fetch_nodes_raw_retries_timeout_and_succeeds(
        self,
        mock_run_kubectl: AsyncMock,
    ) -> None:
        """Node raw fetch should retry timeout failures before succeeding."""
        mock_run_kubectl.side_effect = [
            RuntimeError("request timed out"),
            '{"items": [{"metadata": {"name": "node-a"}}]}',
        ]
        fetcher = NodeFetcher(mock_run_kubectl)

        items = await fetcher.fetch_nodes_raw(request_timeout="8s")

        assert len(items) == 1
        assert mock_run_kubectl.await_count == 2
        first_args = mock_run_kubectl.await_args_list[0].args[0]
        second_args = mock_run_kubectl.await_args_list[1].args[0]
        assert "--request-timeout=8s" in first_args
        assert "--request-timeout=30s" in second_args
        assert "--chunk-size=200" in second_args

    @pytest.mark.asyncio
    async def test_fetch_nodes_raw_raises_non_timeout_error(
        self,
        mock_run_kubectl: AsyncMock,
    ) -> None:
        """Non-timeout node failures should not be retried."""
        mock_run_kubectl.side_effect = RuntimeError("forbidden")
        fetcher = NodeFetcher(mock_run_kubectl)

        with pytest.raises(RuntimeError, match="forbidden"):
            await fetcher.fetch_nodes_raw()

        assert mock_run_kubectl.await_count == 1

    @pytest.mark.asyncio
    async def test_fetch_nodes_uses_raw_items_pipeline(
        self,
        mock_run_kubectl: AsyncMock,
    ) -> None:
        """fetch_nodes should parse NodeInfo objects from raw items."""
        mock_run_kubectl.return_value = (
            '{"items": [{"metadata": {"name": "node-a", "labels": {}}, '
            '"status": {"conditions": [{"type": "Ready", "status": "True"}], '
            '"allocatable": {"cpu": "2", "memory": "8Gi", "pods": "110"}, '
            '"nodeInfo": {"kubeletVersion": "v1.30.0"}}, "spec": {}}]}'
        )
        fetcher = NodeFetcher(mock_run_kubectl)

        nodes = await fetcher.fetch_nodes()

        assert len(nodes) == 1
        assert nodes[0].name == "node-a"
