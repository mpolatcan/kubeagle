"""Tests for cluster fetcher."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from kubeagle.controllers.cluster.fetchers.cluster_fetcher import (
    ClusterFetcher,
)


class TestClusterFetcher:
    """Tests for ClusterFetcher class."""

    @pytest.fixture
    def mock_run_kubectl(self) -> AsyncMock:
        """Create mock run_kubectl function."""
        return AsyncMock()

    @pytest.fixture
    def mock_run_helm(self) -> AsyncMock:
        """Create mock run_helm function."""
        return AsyncMock()

    def test_fetcher_init(self, mock_run_kubectl: AsyncMock, mock_run_helm: AsyncMock) -> None:
        """Test ClusterFetcher initialization."""
        fetcher = ClusterFetcher(
            run_kubectl_func=mock_run_kubectl, run_helm_func=mock_run_helm
        )
        assert fetcher._run_kubectl is mock_run_kubectl
        assert fetcher._run_helm is mock_run_helm

    def test_fetcher_init_no_helm(self, mock_run_kubectl: AsyncMock) -> None:
        """Test ClusterFetcher with only kubectl."""
        fetcher = ClusterFetcher(run_kubectl_func=mock_run_kubectl)
        assert fetcher._run_kubectl is mock_run_kubectl
        assert fetcher._run_helm is None

    @pytest.mark.asyncio
    async def test_check_cluster_connection_success(self, mock_run_kubectl: AsyncMock) -> None:
        """Test check_cluster_connection returns True on success."""
        fetcher = ClusterFetcher(run_kubectl_func=mock_run_kubectl)
        mock_run_kubectl.return_value = "Kubernetes control plane at https://api.example.com"

        result = await fetcher.check_cluster_connection()

        assert result is True
        mock_run_kubectl.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_cluster_connection_failure(self, mock_run_kubectl: AsyncMock) -> None:
        """Test check_cluster_connection returns False on failure."""
        fetcher = ClusterFetcher(run_kubectl_func=mock_run_kubectl)
        mock_run_kubectl.return_value = ""

        result = await fetcher.check_cluster_connection()

        assert result is False

    @pytest.mark.asyncio
    async def test_check_cluster_connection_error(self, mock_run_kubectl: AsyncMock) -> None:
        """Test check_cluster_connection handles errors gracefully."""
        fetcher = ClusterFetcher(run_kubectl_func=mock_run_kubectl)
        mock_run_kubectl.side_effect = OSError("Connection failed")

        result = await fetcher.check_cluster_connection()

        assert result is False

    @pytest.mark.asyncio
    async def test_fetch_helm_releases_success(self, mock_run_kubectl: AsyncMock, mock_run_helm: AsyncMock) -> None:
        """Test fetch_helm_releases returns releases."""
        fetcher = ClusterFetcher(
            run_kubectl_func=mock_run_kubectl, run_helm_func=mock_run_helm
        )

        releases_data = [
            {
                "name": "frontend",
                "namespace": "default",
                "chart": "frontend-1.0.0",
                "version": "1",
                "app_version": "1.0.0",
                "status": "deployed",
            },
        ]
        mock_run_helm.return_value = json.dumps(releases_data)

        result = await fetcher.fetch_helm_releases()

        assert len(result) == 1
        assert result[0].name == "frontend"
        assert result[0].namespace == "default"
        assert result[0].chart == "frontend-1.0.0"
        called_args = mock_run_helm.await_args_list[0].args[0]
        assert "--timeout" not in called_args

    @pytest.mark.asyncio
    async def test_fetch_helm_releases_no_helm(self, mock_run_kubectl: AsyncMock) -> None:
        """Test fetch_helm_releases returns empty list when no helm func."""
        fetcher = ClusterFetcher(run_kubectl_func=mock_run_kubectl)

        result = await fetcher.fetch_helm_releases()

        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_helm_releases_empty(self, mock_run_kubectl: AsyncMock, mock_run_helm: AsyncMock) -> None:
        """Test fetch_helm_releases returns empty list when no releases."""
        fetcher = ClusterFetcher(
            run_kubectl_func=mock_run_kubectl, run_helm_func=mock_run_helm
        )
        mock_run_helm.return_value = ""

        result = await fetcher.fetch_helm_releases()

        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_helm_releases_invalid_json(self, mock_run_kubectl: AsyncMock, mock_run_helm: AsyncMock) -> None:
        """Test fetch_helm_releases handles invalid JSON."""
        fetcher = ClusterFetcher(
            run_kubectl_func=mock_run_kubectl, run_helm_func=mock_run_helm
        )
        mock_run_helm.return_value = "invalid json"

        result = await fetcher.fetch_helm_releases()

        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_helm_releases_for_namespace_success(
        self,
        mock_run_kubectl: AsyncMock,
        mock_run_helm: AsyncMock,
    ) -> None:
        """Namespace helm fetch should parse releases with namespace scope."""
        fetcher = ClusterFetcher(
            run_kubectl_func=mock_run_kubectl, run_helm_func=mock_run_helm
        )
        mock_run_helm.return_value = json.dumps(
            [
                {
                    "name": "svc-a",
                    "namespace": "payments",
                    "chart": "svc-a-1.2.3",
                    "version": "4",
                    "app_version": "1.2.3",
                    "status": "deployed",
                }
            ]
        )

        releases = await fetcher.fetch_helm_releases_for_namespace("payments")

        assert len(releases) == 1
        assert releases[0].namespace == "payments"
        called_args = mock_run_helm.await_args_list[0].args[0]
        assert "-n" in called_args
        assert "payments" in called_args
        assert "--timeout" not in called_args

    @pytest.mark.asyncio
    async def test_fetch_pdbs_success(self, mock_run_kubectl: AsyncMock) -> None:
        """Test fetch_pdbs returns PDBs."""
        fetcher = ClusterFetcher(run_kubectl_func=mock_run_kubectl)

        pdbs_data = {
            "items": [
                {
                    "metadata": {"name": "my-pdb", "namespace": "default"},
                    "spec": {"minAvailable": 1},
                    "status": {"currentHealthy": 3, "desiredHealthy": 3},
                },
            ]
        }
        mock_run_kubectl.return_value = json.dumps(pdbs_data)

        result = await fetcher.fetch_pdbs()

        assert len(result) == 1
        assert result[0]["metadata"]["name"] == "my-pdb"

    @pytest.mark.asyncio
    async def test_fetch_pdbs_empty(self, mock_run_kubectl: AsyncMock) -> None:
        """Test fetch_pdbs returns empty list when no PDBs."""
        fetcher = ClusterFetcher(run_kubectl_func=mock_run_kubectl)
        mock_run_kubectl.return_value = ""

        result = await fetcher.fetch_pdbs()

        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_pdbs_invalid_json(self, mock_run_kubectl: AsyncMock) -> None:
        """Test fetch_pdbs handles invalid JSON."""
        fetcher = ClusterFetcher(run_kubectl_func=mock_run_kubectl)
        mock_run_kubectl.return_value = "invalid json"

        result = await fetcher.fetch_pdbs()

        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_pdbs_for_namespace_success(
        self,
        mock_run_kubectl: AsyncMock,
    ) -> None:
        """Namespace PDB fetch should issue -n scoped request."""
        fetcher = ClusterFetcher(run_kubectl_func=mock_run_kubectl)
        mock_run_kubectl.return_value = json.dumps({"items": []})

        result = await fetcher.fetch_pdbs_for_namespace("payments")

        assert result == []
        called_args = mock_run_kubectl.await_args_list[0].args[0]
        assert "-n" in called_args
        assert "payments" in called_args
