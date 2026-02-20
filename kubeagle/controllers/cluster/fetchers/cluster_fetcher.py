"""Cluster fetcher for cluster controller - fetches cluster-level data from Kubernetes."""

from __future__ import annotations

import json
import logging
from typing import Any

from kubeagle.constants.timeouts import CLUSTER_REQUEST_TIMEOUT
from kubeagle.models.charts.chart_info import HelmReleaseInfo

logger = logging.getLogger(__name__)


class ClusterFetcher:
    """Fetches cluster-level data from Kubernetes cluster."""

    def __init__(
        self, run_kubectl_func: Any, run_helm_func: Any | None = None
    ) -> None:
        """Initialize with kubectl and helm runner functions.

        Args:
            run_kubectl_func: Async function to run kubectl commands
            run_helm_func: Optional async function to run helm commands
        """
        self._run_kubectl = run_kubectl_func
        self._run_helm = run_helm_func

    async def check_cluster_connection(self) -> bool:
        """Check if cluster connection is working.

        Returns:
            True if connected, False otherwise.
        """
        try:
            output = await self._run_kubectl(
                (
                    "version",
                    "--output=json",
                    f"--request-timeout={CLUSTER_REQUEST_TIMEOUT}",
                )
            )
        except OSError:
            return False
        if not output.strip():
            return False
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            # Command succeeded but output wasn't JSON; treat as connected.
            return True
        return bool(data.get("serverVersion"))

    async def fetch_helm_releases(self) -> list[HelmReleaseInfo]:
        """Fetch Helm releases from the cluster.

        Returns:
            List of HelmReleaseInfo objects.
        """
        if self._run_helm is None:
            return []

        try:
            result = await self._run_helm(("list", "-A", "-o", "json"))
            if not result:
                return []

            releases_data = json.loads(result)
            return [
                HelmReleaseInfo(
                    name=r.get("name", ""),
                    namespace=r.get("namespace", ""),
                    chart=r.get("chart", ""),
                    version=r.get("version", ""),
                    app_version=r.get("app_version", ""),
                    status=r.get("status", ""),
                )
                for r in releases_data
            ]

        except (json.JSONDecodeError, Exception):
            logger.exception("Error fetching Helm releases")
            return []

    async def fetch_helm_releases_for_namespace(
        self,
        namespace: str,
    ) -> list[HelmReleaseInfo]:
        """Fetch Helm releases for a single namespace."""
        if self._run_helm is None or not namespace:
            return []

        try:
            result = await self._run_helm(
                ("list", "-n", namespace, "-o", "json")
            )
            if not result:
                return []

            releases_data = json.loads(result)
            return [
                HelmReleaseInfo(
                    name=r.get("name", ""),
                    namespace=r.get("namespace", namespace),
                    chart=r.get("chart", ""),
                    version=r.get("version", ""),
                    app_version=r.get("app_version", ""),
                    status=r.get("status", ""),
                )
                for r in releases_data
            ]

        except (json.JSONDecodeError, Exception):
            logger.exception(
                "Error fetching Helm releases for namespace %s",
                namespace,
            )
            return []

    async def fetch_pdbs(self) -> list[dict[str, Any]]:
        """Fetch PodDisruptionBudgets from the cluster.

        Returns:
            List of PDB dictionaries.
        """
        output = await self._run_kubectl(
            ("get", "pdb", "-A", "-o", "json", f"--request-timeout={CLUSTER_REQUEST_TIMEOUT}")
        )

        if not output:
            return []

        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            logger.exception("Error parsing PDBs JSON")
            return []

        return data.get("items", [])

    async def fetch_pdbs_for_namespace(self, namespace: str) -> list[dict[str, Any]]:
        """Fetch PodDisruptionBudgets from a single namespace."""
        if not namespace:
            return []

        output = await self._run_kubectl(
            (
                "get",
                "pdb",
                "-n",
                namespace,
                "-o",
                "json",
                f"--request-timeout={CLUSTER_REQUEST_TIMEOUT}",
            )
        )

        if not output:
            return []

        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            logger.exception("Error parsing PDBs JSON for namespace %s", namespace)
            return []

        return data.get("items", [])
