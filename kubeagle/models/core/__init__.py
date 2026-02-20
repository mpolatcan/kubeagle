"""Core cluster models."""

from kubeagle.models.core.node_info import NodeInfo, NodeResourceInfo
from kubeagle.models.core.workload_info import SingleReplicaWorkloadInfo
from kubeagle.models.core.workload_inventory_info import (
    WorkloadAssignedNodeDetailInfo,
    WorkloadAssignedPodDetailInfo,
    WorkloadInventoryInfo,
    WorkloadLiveUsageSampleInfo,
)

__all__ = [
    "NodeInfo",
    "NodeResourceInfo",
    "SingleReplicaWorkloadInfo",
    "WorkloadAssignedNodeDetailInfo",
    "WorkloadAssignedPodDetailInfo",
    "WorkloadInventoryInfo",
    "WorkloadLiveUsageSampleInfo",
]
