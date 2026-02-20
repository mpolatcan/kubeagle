"""Tests for core models."""

from __future__ import annotations

from kubeagle.constants.enums import NodeStatus
from kubeagle.models.core.node_info import NodeInfo, NodeResourceInfo
from kubeagle.models.core.workload_info import SingleReplicaWorkloadInfo


class TestNodeInfo:
    """Tests for NodeInfo model."""

    def test_node_info_creation(self) -> None:
        """Test NodeInfo creation."""
        node = NodeInfo(
            name="ip-10-0-1-10.us-east-1.compute.internal",
            status=NodeStatus.READY,
            node_group="default-worker",
            instance_type="m5.large",
            availability_zone="us-east-1a",
            cpu_allocatable=2000.0,
            memory_allocatable=8000000000.0,
            cpu_requests=1500.0,
            cpu_limits=1800.0,
            memory_requests=4000000000.0,
            memory_limits=6000000000.0,
            pod_count=50,
            pod_capacity=110,
        )

        assert node.name == "ip-10-0-1-10.us-east-1.compute.internal"
        assert node.status == NodeStatus.READY
        assert node.pod_count == 50


class TestNodeResourceInfo:
    """Tests for NodeResourceInfo model."""

    def test_node_resource_info_creation(self) -> None:
        """Test NodeResourceInfo creation."""
        info = NodeResourceInfo(
            name="ip-10-0-1-10.us-east-1.compute.internal",
            status=NodeStatus.READY,
            node_group="default-worker",
            instance_type="m5.large",
            availability_zone="us-east-1a",
            kubelet_version="v1.28.0-eks-1234567",
            cpu_allocatable=2000.0,
            memory_allocatable=8000000000.0,
            max_pods=110,
            cpu_requests=1500.0,
            cpu_limits=1800.0,
            memory_requests=4000000000.0,
            memory_limits=6000000000.0,
            pod_count=50,
            cpu_req_pct=75.0,
            cpu_lim_pct=90.0,
            mem_req_pct=50.0,
            mem_lim_pct=75.0,
            pod_pct=45.0,
            is_ready=True,
            is_healthy=True,
            is_cordoned=False,
            conditions={},
            taints=[],
        )

        assert info.name == "ip-10-0-1-10.us-east-1.compute.internal"
        assert info.kubelet_version == "v1.28.0-eks-1234567"
        assert info.cpu_req_pct == 75.0


class TestSingleReplicaWorkloadInfo:
    """Tests for SingleReplicaWorkloadInfo model."""

    def test_single_replica_workload_info_creation(self) -> None:
        """Test SingleReplicaWorkloadInfo creation."""
        workload = SingleReplicaWorkloadInfo(
            name="my-deployment",
            namespace="default",
            kind="Deployment",
            replicas=1,
            ready_replicas=1,
            helm_release="my-release",
            chart_name="my-chart",
            status="Ready",
        )

        assert workload.name == "my-deployment"
        assert workload.replicas == 1
        assert workload.status == "Ready"

    def test_single_replica_workload_info_not_ready(self) -> None:
        """Test SingleReplicaWorkloadInfo for not ready workload."""
        workload = SingleReplicaWorkloadInfo(
            name="my-deployment",
            namespace="default",
            kind="Deployment",
            replicas=1,
            ready_replicas=0,
            helm_release="my-release",
            chart_name="my-chart",
            status="NotReady",
        )

        assert workload.status == "NotReady"
