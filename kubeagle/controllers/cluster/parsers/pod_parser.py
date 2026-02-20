"""Pod parser for cluster controller - parses pod data into structured formats."""

from __future__ import annotations

from typing import Any

from kubeagle.models.teams.distribution import PodDistributionInfo
from kubeagle.utils.resource_parser import memory_str_to_bytes, parse_cpu


class PodParser:
    """Parses pod data into structured formats."""

    _NODE_GROUP_LABELS = (
        "eks.amazonaws.com/nodegroup",
        "alpha.eksctl.io/nodegroup-name",
        "karpenter.sh/nodepool",
        "karpenter.sh/provisioner-name",
        "kops.k8s.io/instancegroup",
    )

    def __init__(self) -> None:
        """Initialize pod parser."""
        pass

    def _get_label_value(
        self, labels: dict[str, str], label_tuples: tuple[str, ...], default: str = "Unknown"
    ) -> str:
        """Extract label value from labels dict using ordered label tuples."""
        for label in label_tuples:
            value = labels.get(label)
            if value:
                return value
        return default

    def parse_pods_by_node(
        self, pods: list[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        """Group pods by node name.

        Args:
            pods: List of pod dictionaries

        Returns:
            Dictionary mapping node name to list of pods.
        """
        pods_by_node: dict[str, list[dict[str, Any]]] = {}
        for pod in pods:
            if pod.get("status", {}).get("phase") in ("Running", "Pending") and (
                node_name := pod.get("spec", {}).get("nodeName")
            ):
                pods_by_node.setdefault(node_name, []).append(pod)
        return pods_by_node

    def parse_distribution(
        self,
        nodes: list[dict[str, Any]],
        pods: list[dict[str, Any]],
    ) -> PodDistributionInfo:
        """Analyze pod distribution across nodes and node groups.

        Args:
            nodes: List of node dictionaries
            pods: List of pod dictionaries

        Returns:
            PodDistributionInfo with distribution statistics.
        """
        pods_by_node = self.parse_pods_by_node(pods)

        # Collect node info and pod counts
        node_info_by_name: dict[str, dict[str, Any]] = {}
        pod_counts: list[int] = []

        for node in nodes:
            metadata = node.get("metadata", {})
            labels = metadata.get("labels", {})

            node_name = metadata.get("name", "Unknown")
            node_group = self._get_label_value(labels, self._NODE_GROUP_LABELS)

            node_pods = pods_by_node.get(node_name, [])
            pod_count = len(node_pods)
            pod_counts.append(pod_count)

            node_info_by_name[node_name] = {
                "name": node_name,
                "node_group": node_group,
                "pod_count": pod_count,
            }

        # Calculate statistics
        total_pods = sum(pod_counts)
        min_pods = min(pod_counts) if pod_counts else 0
        max_pods = max(pod_counts) if pod_counts else 0
        avg_pods = sum(pod_counts) / len(pod_counts) if pod_counts else 0.0

        # Calculate P95
        sorted_counts = sorted(pod_counts)
        p95_idx = int(len(sorted_counts) * 0.95)
        p95_pods = sorted_counts[p95_idx] if sorted_counts else 0

        # Find high pod nodes (top 10)
        high_pod_nodes = []
        for node_name in sorted(
            node_info_by_name.keys(),
            key=lambda n: node_info_by_name[n]["pod_count"],
            reverse=True,
        )[:10]:
            info = node_info_by_name[node_name]
            high_pod_nodes.append(
                {
                    "name": info["name"],
                    "node_group": info["node_group"],
                    "pod_count": info["pod_count"],
                    "cpu_pct": 0.0,
                    "mem_pct": 0.0,
                }
            )

        # Group by node group
        by_node_group: dict[str, dict[str, Any]] = {}
        for info in node_info_by_name.values():
            ng = info["node_group"]
            if ng not in by_node_group:
                by_node_group[ng] = {
                    "node_count": 0,
                    "total_pods": 0,
                    "pod_counts": [],
                }
            by_node_group[ng]["node_count"] += 1
            by_node_group[ng]["total_pods"] += info["pod_count"]
            by_node_group[ng]["pod_counts"].append(info["pod_count"])

        # Calculate averages per node group
        for ng_data in by_node_group.values():
            counts = ng_data["pod_counts"]
            ng_data["avg_pods_per_node"] = sum(counts) / len(counts) if counts else 0.0
            ng_data["min_pods"] = min(counts) if counts else 0
            ng_data["max_pods"] = max(counts) if counts else 0

        return PodDistributionInfo(
            total_pods=total_pods,
            min_pods_per_node=min_pods,
            max_pods_per_node=max_pods,
            avg_pods_per_node=avg_pods,
            p95_pods_per_node=p95_pods,
            high_pod_nodes=high_pod_nodes,
            by_node_group=by_node_group,
        )

    def parse_pod_requests(
        self, pods: list[dict[str, Any]]
    ) -> dict[str, dict[str, float]]:
        """Calculate CPU/Memory request and limit statistics.

        Args:
            pods: List of pod dictionaries

        Returns:
            Dictionary with request/limit statistics for CPU and memory.
        """
        cpu_requests_by_node: dict[str, list[float]] = {}
        memory_requests_by_node: dict[str, list[float]] = {}
        cpu_limits_by_node: dict[str, list[float]] = {}
        memory_limits_by_node: dict[str, list[float]] = {}

        for pod in pods:
            pod_status = pod.get("status", {})
            if pod_status.get("phase") not in ("Running", "Pending"):
                continue

            node_name = pod.get("spec", {}).get("nodeName", "Unknown")
            pod_spec = pod.get("spec", {})

            node_cpu_request_total = 0.0
            node_mem_request_total = 0.0
            node_cpu_limit_total = 0.0
            node_mem_limit_total = 0.0

            for container in pod_spec.get("containers", []):
                resources = container.get("resources", {})
                requests = resources.get("requests", {})
                limits = resources.get("limits", {})

                cpu_str = requests.get("cpu", "0")
                mem_str = requests.get("memory", "0Ki")
                cpu_limit_str = limits.get("cpu", "0")
                mem_limit_str = limits.get("memory", "0Ki")

                node_cpu_request_total += parse_cpu(cpu_str) * 1000
                node_mem_request_total += memory_str_to_bytes(mem_str)
                node_cpu_limit_total += parse_cpu(cpu_limit_str) * 1000
                node_mem_limit_total += memory_str_to_bytes(mem_limit_str)

            if node_cpu_request_total > 0:
                cpu_requests_by_node.setdefault(node_name, []).append(node_cpu_request_total)
            if node_mem_request_total > 0:
                memory_requests_by_node.setdefault(node_name, []).append(node_mem_request_total)
            if node_cpu_limit_total > 0:
                cpu_limits_by_node.setdefault(node_name, []).append(node_cpu_limit_total)
            if node_mem_limit_total > 0:
                memory_limits_by_node.setdefault(node_name, []).append(node_mem_limit_total)

        def calc_stats(data_dict: dict[str, list[float]]) -> dict[str, float]:
            all_values = [v for vals in data_dict.values() for v in vals]
            if not all_values:
                return {"min": 0, "avg": 0.0, "max": 0, "p95": 0}

            sorted_values = sorted(all_values)
            p95_idx = int(len(sorted_values) * 0.95)

            return {
                "min": min(all_values),
                "avg": sum(all_values) / len(all_values),
                "max": max(all_values),
                "p95": sorted_values[p95_idx] if sorted_values else 0,
            }

        cpu_request_stats = calc_stats(cpu_requests_by_node)
        memory_request_stats = calc_stats(memory_requests_by_node)

        return {
            "cpu_request_stats": cpu_request_stats,
            "memory_request_stats": memory_request_stats,
            "cpu_limit_stats": calc_stats(cpu_limits_by_node),
            "memory_limit_stats": calc_stats(memory_limits_by_node),
            # Backward-compatible aliases used in existing presenter/tests.
            "cpu_stats": cpu_request_stats,
            "memory_stats": memory_request_stats,
        }
