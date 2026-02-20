"""Tests for top metrics fetcher."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from kubeagle.controllers.cluster.fetchers.top_metrics_fetcher import (
    TopMetricsFetcher,
)


class TestTopMetricsFetcher:
    """Tests for TopMetricsFetcher class."""

    @pytest.fixture
    def mock_run_kubectl(self) -> AsyncMock:
        return AsyncMock()

    def test_fetcher_init(self, mock_run_kubectl: AsyncMock) -> None:
        fetcher = TopMetricsFetcher(mock_run_kubectl)
        assert fetcher._run_kubectl is mock_run_kubectl

    @pytest.mark.asyncio
    async def test_fetch_top_nodes_parses_output(self, mock_run_kubectl: AsyncMock) -> None:
        mock_run_kubectl.return_value = "\n".join(
            [
                "node-a 123m 6% 1024Mi 20%",
                "node-b 250m 10% 2Gi 40%",
            ]
        )
        fetcher = TopMetricsFetcher(mock_run_kubectl)

        rows = await fetcher.fetch_top_nodes(request_timeout="8s")

        assert len(rows) == 2
        assert rows[0]["node_name"] == "node-a"
        assert rows[0]["cpu_mcores"] == 123.0
        assert rows[0]["memory_bytes"] == 1024 * 1024 * 1024
        assert rows[1]["node_name"] == "node-b"
        assert rows[1]["cpu_mcores"] == 250.0
        assert rows[1]["memory_bytes"] == 2 * 1024 * 1024 * 1024

    @pytest.mark.asyncio
    async def test_fetch_top_pods_parses_output(self, mock_run_kubectl: AsyncMock) -> None:
        mock_run_kubectl.return_value = "\n".join(
            [
                "team-a api-123 50m 200Mi",
                "team-a worker-456 250m 1Gi",
            ]
        )
        fetcher = TopMetricsFetcher(mock_run_kubectl)

        rows = await fetcher.fetch_top_pods_all_namespaces(request_timeout="8s")

        assert len(rows) == 2
        assert rows[0]["namespace"] == "team-a"
        assert rows[0]["pod_name"] == "api-123"
        assert rows[0]["cpu_mcores"] == 50.0
        assert rows[0]["memory_bytes"] == 200 * 1024 * 1024
        assert rows[1]["pod_name"] == "worker-456"
        assert rows[1]["cpu_mcores"] == 250.0
        assert rows[1]["memory_bytes"] == 1024 * 1024 * 1024

    @pytest.mark.asyncio
    async def test_fetch_top_nodes_skips_malformed_lines(
        self,
        mock_run_kubectl: AsyncMock,
    ) -> None:
        mock_run_kubectl.return_value = "\n".join(
            [
                "malformed",
                "node-a 123m 6% 1024Mi 20%",
            ]
        )
        fetcher = TopMetricsFetcher(mock_run_kubectl)

        rows = await fetcher.fetch_top_nodes()

        assert len(rows) == 1
        assert rows[0]["node_name"] == "node-a"

    @pytest.mark.asyncio
    async def test_fetch_top_pods_retries_timeout_then_succeeds(
        self,
        mock_run_kubectl: AsyncMock,
    ) -> None:
        mock_run_kubectl.side_effect = [
            RuntimeError("request timed out"),
            "team-a api-123 50m 200Mi",
        ]
        fetcher = TopMetricsFetcher(mock_run_kubectl)

        rows = await fetcher.fetch_top_pods_all_namespaces(request_timeout="8s")

        assert len(rows) == 1
        assert mock_run_kubectl.await_count == 2
        first_args = mock_run_kubectl.await_args_list[0].args[0]
        second_args = mock_run_kubectl.await_args_list[1].args[0]
        assert "--request-timeout=8s" in first_args
        assert "--request-timeout=30s" in second_args

    @pytest.mark.asyncio
    async def test_fetch_top_nodes_raises_non_timeout_errors(
        self,
        mock_run_kubectl: AsyncMock,
    ) -> None:
        mock_run_kubectl.side_effect = RuntimeError("forbidden")
        fetcher = TopMetricsFetcher(mock_run_kubectl)

        with pytest.raises(RuntimeError, match="forbidden"):
            await fetcher.fetch_top_nodes()

        assert mock_run_kubectl.await_count == 1

    @pytest.mark.asyncio
    async def test_fetch_top_nodes_for_names_chunks_requests(
        self,
        mock_run_kubectl: AsyncMock,
    ) -> None:
        mock_run_kubectl.side_effect = [
            "node-a 100m 5% 1000Mi 20%",
            "node-b 200m 10% 2000Mi 40%",
            "node-c 300m 15% 3000Mi 60%",
        ]
        fetcher = TopMetricsFetcher(mock_run_kubectl)
        fetcher._TARGET_TOP_NODE_CHUNK_SIZE = 2

        rows = await fetcher.fetch_top_nodes_for_names(
            ["node-a", "node-b", "node-c"],
            request_timeout="8s",
        )

        assert len(rows) == 3
        assert rows[2]["node_name"] == "node-c"
        assert mock_run_kubectl.await_count == 3
        first_args = mock_run_kubectl.await_args_list[0].args[0]
        second_args = mock_run_kubectl.await_args_list[1].args[0]
        third_args = mock_run_kubectl.await_args_list[2].args[0]
        assert first_args[:3] == ("top", "node", "node-a")
        assert second_args[:3] == ("top", "node", "node-b")
        assert third_args[:3] == ("top", "node", "node-c")

    @pytest.mark.asyncio
    async def test_fetch_top_pods_for_namespace_parses_scoped_output(
        self,
        mock_run_kubectl: AsyncMock,
    ) -> None:
        mock_run_kubectl.side_effect = [
            "api-123 50m 200Mi",
            "worker-456 250m 1Gi",
        ]
        fetcher = TopMetricsFetcher(mock_run_kubectl)

        rows = await fetcher.fetch_top_pods_for_namespace(
            "team-a",
            ["api-123", "worker-456"],
            request_timeout="8s",
        )

        assert len(rows) == 2
        assert rows[0]["namespace"] == "team-a"
        assert rows[0]["pod_name"] == "api-123"
        assert rows[1]["pod_name"] == "worker-456"
        args = mock_run_kubectl.await_args_list[0].args[0]
        assert args[0:4] == ("top", "pod", "-n", "team-a")
        assert args[4] == "api-123"
        second_args = mock_run_kubectl.await_args_list[1].args[0]
        assert second_args[4] == "worker-456"
        assert "--request-timeout=8s" in args

    @pytest.mark.asyncio
    async def test_fetch_top_pods_for_namespace_chunks_requests(
        self,
        mock_run_kubectl: AsyncMock,
    ) -> None:
        mock_run_kubectl.side_effect = [
            "api-1 10m 20Mi",
            "api-2 20m 40Mi",
        ]
        fetcher = TopMetricsFetcher(mock_run_kubectl)
        fetcher._TARGET_TOP_POD_CHUNK_SIZE = 1

        rows = await fetcher.fetch_top_pods_for_namespace(
            "team-a",
            ["api-1", "api-2"],
        )

        assert len(rows) == 2
        assert rows[0]["namespace"] == "team-a"
        assert mock_run_kubectl.await_count == 2

    @pytest.mark.asyncio
    async def test_fetch_top_pods_for_namespace_empty_inputs_return_empty(
        self,
        mock_run_kubectl: AsyncMock,
    ) -> None:
        fetcher = TopMetricsFetcher(mock_run_kubectl)

        assert await fetcher.fetch_top_pods_for_namespace("", ["a"]) == []
        assert await fetcher.fetch_top_pods_for_namespace("team-a", []) == []
        assert mock_run_kubectl.await_count == 0
