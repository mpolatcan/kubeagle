"""Distribution analysis utilities for EKS cluster data operations."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any, cast

logger = logging.getLogger(__name__)

# Label constants for node metadata extraction
_NODE_GROUP_LABELS = (
    "eks.amazonaws.com/nodegroup",
    "alpha.eksctl.io/nodegroup-name",
    "karpenter.sh/nodepool",
    "karpenter.sh/provisioner-name",
    "kops.k8s.io/instancegroup",
)
_INSTANCE_TYPE_LABELS = (
    "node.kubernetes.io/instance-type",
    "beta.kubernetes.io/instance-type",
)
_AZ_LABELS = (
    "topology.kubernetes.io/zone",
    "failure-domain.beta.kubernetes.io/zone",
)
_UNKNOWN_LABEL = "Unknown"


def _get_label_value(
    labels: dict[str, str], label_tuples: tuple[str, ...], default: str = "Unknown"
) -> str:
    """Extract label value from labels dict using ordered label tuples.

    Args:
        labels: Dictionary of node labels.
        label_tuples: Tuple of label keys to check in order.
        default: Default value if no label found.

    Returns:
        Label value or default.
    """
    for label in label_tuples:
        value = labels.get(label)
        if value:
            return value
    return default


class DistributionAnalyzer:
    """Analyzes distribution of cluster resources across various dimensions."""

    def __init__(self, nodes_output: str, pods_output: str | None = None) -> None:
        """Initialize with cluster data.

        Args:
            nodes_output: JSON output from kubectl get nodes.
            pods_output: Optional JSON output from kubectl get pods.
        """
        self.nodes_data = self._parse_json(nodes_output)
        self.pods_data = self._parse_json(pods_output) if pods_output else {"items": []}

    def _parse_json(self, output: str) -> dict[str, Any]:
        """Safely parse JSON output."""
        if not output:
            return {"items": []}
        try:
            return cast("dict[str, Any]", json.loads(output))
        except json.JSONDecodeError:
            logger.exception("Error parsing JSON")
            return {"items": []}

    @property
    def pods_by_node(self) -> dict[str, list[dict[str, Any]]]:
        """Build and cache pods index by node name."""
        if not hasattr(self, "_pods_by_node"):
            self._pods_by_node: dict[str, list[dict[str, Any]]] = {}
            for pod in self.pods_data.get("items", []):
                pod_status = pod.get("status", {})
                if pod_status.get("phase") in ("Running", "Pending") and (
                    node_name := pod.get("spec", {}).get("nodeName")
                ):
                    self._pods_by_node.setdefault(node_name, []).append(pod)
        return self._pods_by_node

    def get_node_conditions_summary(self) -> dict[str, dict[str, int]]:
        """Analyze node conditions across all nodes.

        Returns:
            Dict mapping condition type to status counts.
        """
        condition_types = [
            "Ready",
            "MemoryPressure",
            "DiskPressure",
            "PIDPressure",
            "NetworkUnavailable",
        ]
        conditions: dict[str, dict[str, int]] = {
            cond: {"True": 0, "False": 0, "Unknown": 0} for cond in condition_types
        }

        for node in self.nodes_data.get("items", []):
            status = node.get("status", {})
            for condition in status.get("conditions", []):
                cond_type = condition.get("type")
                if cond_type in conditions:
                    status_val = condition.get("status", "Unknown")
                    if status_val in conditions[cond_type]:
                        conditions[cond_type][status_val] += 1
                    else:
                        conditions[cond_type]["Unknown"] += 1

        return conditions

    def get_node_taints_analysis(self) -> dict[str, Any]:
        """Analyze taints distribution across nodes.

        Returns:
            Dict with total count and taint distribution.
        """
        nodes_with_taints = 0
        taint_distribution: dict[str, dict[str, Any]] = {}

        for node in self.nodes_data.get("items", []):
            spec = node.get("spec", {})
            taints = spec.get("taints", [])

            if taints:
                nodes_with_taints += 1

            for taint in taints:
                key = taint.get("key", "")
                effect = taint.get("effect", "Unknown")
                taint_key = f"{key}={taint.get('value', '')}" if key else effect

                if taint_key not in taint_distribution:
                    taint_distribution[taint_key] = {"effect": effect, "count": 0}
                taint_distribution[taint_key]["count"] += 1

        return {
            "total_nodes_with_taints": nodes_with_taints,
            "taint_distribution": taint_distribution,
        }

    def get_kubelet_version_distribution(self) -> dict[str, int]:
        """Count nodes by kubelet version.

        Returns:
            Dict mapping kubelet version to node count.
        """
        version_counts: dict[str, int] = {}

        for node in self.nodes_data.get("items", []):
            status = node.get("status", {})
            kubelet_version = status.get("nodeInfo", {}).get("kubeletVersion", "Unknown")
            normalized_version = kubelet_version.lstrip("v")

            if normalized_version:
                version_counts[normalized_version] = (
                    version_counts.get(normalized_version, 0) + 1
                )

        return version_counts

    def get_instance_type_distribution(self) -> dict[str, int]:
        """Count nodes by instance type.

        Returns:
            Dict mapping instance type to node count.
        """
        type_counts: dict[str, int] = {}

        for node in self.nodes_data.get("items", []):
            metadata = node.get("metadata", {})
            labels = metadata.get("labels", {})

            instance_type = None
            for label in _INSTANCE_TYPE_LABELS:
                instance_type = labels.get(label)
                if instance_type:
                    break

            if instance_type:
                type_counts[instance_type] = type_counts.get(instance_type, 0) + 1

        return type_counts

    def get_az_distribution(self) -> dict[str, int]:
        """Count nodes by availability zone.

        Returns:
            Dict mapping AZ to node count.
        """
        az_counts: dict[str, int] = {}

        for node in self.nodes_data.get("items", []):
            metadata = node.get("metadata", {})
            labels = metadata.get("labels", {})

            az = None
            for label in _AZ_LABELS:
                az = labels.get(label)
                if az:
                    break

            if az:
                az_counts[az] = az_counts.get(az, 0) + 1

        return az_counts

    def get_node_groups_az_matrix(self) -> dict[str, dict[str, int]]:
        """Cross-tabulation of node groups by availability zone.

        Returns:
            Dict mapping node group to AZ distribution.
        """
        matrix: dict[str, dict[str, int]] = {}

        for node in self.nodes_data.get("items", []):
            metadata = node.get("metadata", {})
            labels = metadata.get("labels", {})

            node_group = _get_label_value(labels, _NODE_GROUP_LABELS, _UNKNOWN_LABEL)
            az = _UNKNOWN_LABEL
            for label in _AZ_LABELS:
                az = labels.get(label, _UNKNOWN_LABEL)
                if az != _UNKNOWN_LABEL:
                    break

            if node_group not in matrix:
                matrix[node_group] = {}
            matrix[node_group][az] = matrix[node_group].get(az, 0) + 1

        return matrix

    def get_high_pod_count_nodes(
        self, threshold_pct: float = 80.0
    ) -> list[dict[str, Any]]:
        """Identify nodes approaching pod capacity.

        Args:
            threshold_pct: Percentage threshold to consider "high" (default: 80.0)

        Returns:
            List of nodes with pod count percentage at or above threshold.
        """
        high_pod_nodes: list[dict[str, Any]] = []

        for node in self.nodes_data.get("items", []):
            metadata = node.get("metadata", {})
            status = node.get("status", {})
            labels = metadata.get("labels", {})

            node_name = metadata.get("name", "Unknown")
            node_group = _get_label_value(labels, _NODE_GROUP_LABELS)

            allocatable = status.get("allocatable", {})
            max_pods_str = allocatable.get("pods", "110")
            try:
                max_pods = int(float(max_pods_str))
            except (ValueError, TypeError):
                max_pods = 110

            pod_count = len(self.pods_by_node.get(node_name, []))
            pod_pct = (pod_count / max_pods * 100) if max_pods > 0 else 0.0

            if pod_pct >= threshold_pct:
                high_pod_nodes.append({
                    "name": node_name,
                    "node_group": node_group,
                    "pod_count": pod_count,
                    "max_pods": max_pods,
                    "pod_pct": pod_pct,
                })

        high_pod_nodes.sort(key=lambda x: x["pod_pct"], reverse=True)
        return high_pod_nodes

    def get_all_distributions(self) -> dict[str, Any]:
        """Get all distribution analyses in one call.

        Returns:
            Dictionary containing all distribution analysis results.
        """
        return {
            "node_conditions": self.get_node_conditions_summary(),
            "node_taints": self.get_node_taints_analysis(),
            "kubelet_versions": self.get_kubelet_version_distribution(),
            "instance_types": self.get_instance_type_distribution(),
            "availability_zones": self.get_az_distribution(),
            "node_groups_az_matrix": self.get_node_groups_az_matrix(),
            "high_pod_nodes": self.get_high_pod_count_nodes(),
        }


async def fetch_and_analyze_distributions(
    run_kubectl: Callable[..., Any],
) -> dict[str, Any]:
    """Convenience function to fetch and analyze all distributions.

    Args:
        run_kubectl: Async function that runs kubectl commands.

    Returns:
        Dictionary with all distribution analyses.
    """
    import asyncio

    nodes_output, pods_output = await asyncio.gather(
        asyncio.to_thread(run_kubectl, ("get", "nodes", "-o", "json")),
        asyncio.to_thread(run_kubectl, ("get", "pods", "-A", "-o", "json")),
        return_exceptions=True,
    )

    if isinstance(nodes_output, Exception):
        logger.exception("Error fetching nodes")
        nodes_output = ""
    if isinstance(pods_output, Exception):
        logger.exception("Error fetching pods")
        pods_output = ""

    analyzer = DistributionAnalyzer(nodes_output, pods_output)
    return analyzer.get_all_distributions()


__all__ = ["DistributionAnalyzer", "fetch_and_analyze_distributions", "_get_label_value"]
