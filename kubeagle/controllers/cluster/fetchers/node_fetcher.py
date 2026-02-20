"""Node fetcher for cluster controller - fetches node data from Kubernetes cluster."""

from __future__ import annotations

import json
import logging
from typing import Any

from kubeagle.constants.enums import NodeStatus
from kubeagle.constants.timeouts import CLUSTER_REQUEST_TIMEOUT
from kubeagle.models.core.node_info import NodeInfo
from kubeagle.utils.resource_parser import memory_str_to_bytes, parse_cpu

logger = logging.getLogger(__name__)

# Constants for node label fallback values
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


def _get_label_value(
    labels: dict[str, str], label_tuples: tuple[str, ...], default: str = "Unknown"
) -> str:
    """Extract label value from labels dict using ordered label tuples."""
    for label in label_tuples:
        value = labels.get(label)
        if value:
            return value
    return default


class NodeFetcher:
    """Fetches node data from Kubernetes cluster."""

    _NODES_CHUNK_SIZE = 200
    _RETRY_REQUEST_TIMEOUT = "45s"
    _TIMEOUT_ERROR_TOKENS = (
        "timed out",
        "timeout",
        "deadline exceeded",
        "i/o timeout",
        "context deadline exceeded",
    )

    def __init__(self, run_kubectl_func: Any) -> None:
        """Initialize with kubectl runner function.

        Args:
            run_kubectl_func: Async function to run kubectl commands
        """
        self._run_kubectl = run_kubectl_func

    @classmethod
    def _is_timeout_error(cls, error: Exception) -> bool:
        """Return True when error indicates timeout-like failure."""
        message = str(error).lower()
        return any(token in message for token in cls._TIMEOUT_ERROR_TOKENS)

    def _build_nodes_args(self, request_timeout: str) -> tuple[str, ...]:
        """Build kubectl args for fetching nodes."""
        return (
            "get",
            "nodes",
            "-o",
            "json",
            f"--chunk-size={self._NODES_CHUNK_SIZE}",
            f"--request-timeout={request_timeout}",
        )

    async def fetch_nodes_raw(
        self,
        request_timeout: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch raw node dictionaries with timeout-aware retries."""
        timeout_arg = request_timeout or CLUSTER_REQUEST_TIMEOUT
        candidate_timeouts = (
            timeout_arg,
            CLUSTER_REQUEST_TIMEOUT,
            self._RETRY_REQUEST_TIMEOUT,
        )
        attempt_timeouts: list[str] = []
        for timeout in candidate_timeouts:
            if timeout not in attempt_timeouts:
                attempt_timeouts.append(timeout)

        last_error: Exception | None = None
        for attempt, timeout in enumerate(attempt_timeouts, start=1):
            args = self._build_nodes_args(timeout)
            try:
                output = await self._run_kubectl(args)
                if not output:
                    return []
                data = json.loads(output)
                return data.get("items", [])
            except json.JSONDecodeError:
                logger.exception("Error parsing nodes JSON")
                return []
            except Exception as exc:
                last_error = exc
                is_retryable = self._is_timeout_error(exc)
                has_next_attempt = attempt < len(attempt_timeouts)
                if is_retryable and has_next_attempt:
                    logger.warning(
                        "Node fetch timed out (attempt %s/%s with %s), retrying",
                        attempt,
                        len(attempt_timeouts),
                        timeout,
                    )
                    continue
                raise

        if last_error is not None:
            raise last_error
        return []

    async def fetch_nodes(self) -> list[NodeInfo]:
        """Fetch and parse kubectl get nodes.

        Returns:
            List of NodeInfo objects.
        """
        items = await self.fetch_nodes_raw()

        nodes = []

        for item in items:
            metadata = item.get("metadata", {})
            status = item.get("status", {})
            spec = item.get("spec", {})
            labels = metadata.get("labels", {})

            name = metadata.get("name", "Unknown")

            # Determine node status
            node_status = NodeStatus.UNKNOWN
            conditions_dict: dict[str, str] = {}
            for condition in status.get("conditions", []):
                if (
                    condition.get("type") == "Ready"
                    and condition.get("status") == "True"
                ):
                    node_status = NodeStatus.READY
                # Build conditions dict
                cond_type = condition.get("type")
                cond_status = condition.get("status", "")
                if cond_type:
                    conditions_dict[cond_type] = cond_status

            # Parse node labels for node group
            node_group = _get_label_value(labels, _NODE_GROUP_LABELS)

            # Get instance type from labels
            instance_type = _get_label_value(labels, _INSTANCE_TYPE_LABELS)

            # Get availability zone
            az = _get_label_value(labels, _AZ_LABELS)

            # Parse capacity and allocatable
            allocatable = status.get("allocatable", {})
            cpu_allocatable = parse_cpu(allocatable.get("cpu", "0")) * 1000
            memory_allocatable = memory_str_to_bytes(
                allocatable.get("memory", "0Ki")
            )

            # Get max pods
            max_pods_str = allocatable.get("pods", "110")
            try:
                pod_capacity = int(float(max_pods_str))
            except (ValueError, TypeError):
                pod_capacity = 110

            # Get kubelet version
            kubelet_version = status.get("nodeInfo", {}).get("kubeletVersion", "")

            # Get taints
            taints = spec.get("taints", [])

            nodes.append(
                NodeInfo(
                    name=name,
                    status=node_status,
                    node_group=node_group,
                    instance_type=instance_type,
                    availability_zone=az,
                    cpu_allocatable=cpu_allocatable,
                    memory_allocatable=memory_allocatable,
                    cpu_requests=0.0,
                    memory_requests=0.0,
                    cpu_limits=0.0,
                    memory_limits=0.0,
                    pod_count=0,
                    pod_capacity=pod_capacity,
                    kubelet_version=kubelet_version,
                    conditions=conditions_dict,
                    taints=taints,
                )
            )

        return nodes
