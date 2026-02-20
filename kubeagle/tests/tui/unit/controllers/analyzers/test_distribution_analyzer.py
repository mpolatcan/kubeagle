"""Tests for distribution analyzer."""

from __future__ import annotations

import json

from kubeagle.controllers.analyzers.distribution_analyzer import (
    DistributionAnalyzer,
    _get_label_value,
)


class TestGetLabelValue:
    """Tests for _get_label_value helper function."""

    def test_found_first_label(self) -> None:
        """Test returns first matching label value."""
        labels = {
            "eks.amazonaws.com/nodegroup": "worker",
            "other-label": "other",
        }
        result = _get_label_value(labels, ("eks.amazonaws.com/nodegroup", "karpenter.sh/nodepool"))
        assert result == "worker"

    def test_fallback_to_second_label(self) -> None:
        """Test falls back to second label if first not found."""
        labels = {
            "karpenter.sh/nodepool": "karpenter-worker",
        }
        result = _get_label_value(labels, ("eks.amazonaws.com/nodegroup", "karpenter.sh/nodepool"))
        assert result == "karpenter-worker"

    def test_returns_default(self) -> None:
        """Test returns default when no labels found."""
        labels = {"other-label": "value"}
        result = _get_label_value(labels, ("eks.amazonaws.com/nodegroup", "karpenter.sh/nodepool"))
        assert result == "Unknown"


class TestDistributionAnalyzer:
    """Tests for DistributionAnalyzer class."""

    def test_analyzer_init_empty(self) -> None:
        """Test DistributionAnalyzer with empty data."""
        analyzer = DistributionAnalyzer("{}", "{}")

        # Empty JSON object {} has no "items" key, so it parses as {}
        assert analyzer.nodes_data == {}
        assert analyzer.pods_data == {}

    def test_analyzer_init_invalid_json(self) -> None:
        """Test DistributionAnalyzer handles invalid JSON."""
        analyzer = DistributionAnalyzer("invalid", "also invalid")

        assert analyzer.nodes_data == {"items": []}
        assert analyzer.pods_data == {"items": []}


# =============================================================================
# Helper to build node JSON
# =============================================================================


def _make_nodes_json(nodes: list[dict]) -> str:
    """Create a valid kubectl-style nodes JSON string."""
    return json.dumps({"items": nodes})


def _make_pods_json(pods: list[dict]) -> str:
    """Create a valid kubectl-style pods JSON string."""
    return json.dumps({"items": pods})


def _make_node(
    name: str = "node-1",
    ready: str = "True",
    kubelet_version: str = "v1.28.3",
    instance_type: str = "m5.large",
    az: str = "us-east-1a",
    max_pods: str = "110",
    taints: list | None = None,
) -> dict:
    """Create a node dict with standard structure."""
    node = {
        "metadata": {
            "name": name,
            "labels": {
                "node.kubernetes.io/instance-type": instance_type,
                "topology.kubernetes.io/zone": az,
                "eks.amazonaws.com/nodegroup": "default-group",
            },
        },
        "status": {
            "conditions": [
                {"type": "Ready", "status": ready},
                {"type": "MemoryPressure", "status": "False"},
                {"type": "DiskPressure", "status": "False"},
                {"type": "PIDPressure", "status": "False"},
            ],
            "nodeInfo": {"kubeletVersion": kubelet_version},
            "allocatable": {"pods": max_pods},
        },
        "spec": {},
    }
    if taints:
        node["spec"]["taints"] = taints
    return node


def _make_pod(name: str, node_name: str, namespace: str = "default") -> dict:
    """Create a pod dict with standard structure."""
    return {
        "metadata": {"name": name, "namespace": namespace},
        "spec": {"nodeName": node_name},
        "status": {"phase": "Running"},
    }


# =============================================================================
# get_node_conditions_summary TESTS
# =============================================================================


class TestGetNodeConditionsSummary:
    """Tests for DistributionAnalyzer.get_node_conditions_summary()."""

    def test_empty_nodes(self) -> None:
        """Test conditions summary with no nodes."""
        analyzer = DistributionAnalyzer(_make_nodes_json([]))
        result = analyzer.get_node_conditions_summary()
        assert result["Ready"]["True"] == 0
        assert result["Ready"]["False"] == 0

    def test_nodes_with_conditions(self) -> None:
        """Test conditions summary with multiple nodes."""
        nodes = [
            _make_node(name="n1", ready="True"),
            _make_node(name="n2", ready="True"),
            _make_node(name="n3", ready="False"),
        ]
        analyzer = DistributionAnalyzer(_make_nodes_json(nodes))
        result = analyzer.get_node_conditions_summary()
        assert result["Ready"]["True"] == 2
        assert result["Ready"]["False"] == 1
        assert result["MemoryPressure"]["False"] == 3


# =============================================================================
# get_kubelet_version_distribution TESTS
# =============================================================================


class TestGetKubeletVersionDistribution:
    """Tests for DistributionAnalyzer.get_kubelet_version_distribution()."""

    def test_empty_nodes(self) -> None:
        """Test version distribution with no nodes."""
        analyzer = DistributionAnalyzer(_make_nodes_json([]))
        result = analyzer.get_kubelet_version_distribution()
        assert result == {}

    def test_mixed_versions(self) -> None:
        """Test version distribution with mixed kubelet versions."""
        nodes = [
            _make_node(name="n1", kubelet_version="v1.28.3"),
            _make_node(name="n2", kubelet_version="v1.28.3"),
            _make_node(name="n3", kubelet_version="v1.29.1"),
        ]
        analyzer = DistributionAnalyzer(_make_nodes_json(nodes))
        result = analyzer.get_kubelet_version_distribution()
        assert result["1.28.3"] == 2
        assert result["1.29.1"] == 1


# =============================================================================
# get_instance_type_distribution TESTS
# =============================================================================


class TestGetInstanceTypeDistribution:
    """Tests for DistributionAnalyzer.get_instance_type_distribution()."""

    def test_empty_nodes(self) -> None:
        """Test instance type distribution with no nodes."""
        analyzer = DistributionAnalyzer(_make_nodes_json([]))
        result = analyzer.get_instance_type_distribution()
        assert result == {}

    def test_mixed_instance_types(self) -> None:
        """Test instance type distribution with mixed types."""
        nodes = [
            _make_node(name="n1", instance_type="m5.large"),
            _make_node(name="n2", instance_type="m5.large"),
            _make_node(name="n3", instance_type="c5.xlarge"),
        ]
        analyzer = DistributionAnalyzer(_make_nodes_json(nodes))
        result = analyzer.get_instance_type_distribution()
        assert result["m5.large"] == 2
        assert result["c5.xlarge"] == 1


# =============================================================================
# get_az_distribution TESTS
# =============================================================================


class TestGetAZDistribution:
    """Tests for DistributionAnalyzer.get_az_distribution()."""

    def test_empty_nodes(self) -> None:
        """Test AZ distribution with no nodes."""
        analyzer = DistributionAnalyzer(_make_nodes_json([]))
        result = analyzer.get_az_distribution()
        assert result == {}

    def test_mixed_azs(self) -> None:
        """Test AZ distribution with mixed availability zones."""
        nodes = [
            _make_node(name="n1", az="us-east-1a"),
            _make_node(name="n2", az="us-east-1b"),
            _make_node(name="n3", az="us-east-1a"),
        ]
        analyzer = DistributionAnalyzer(_make_nodes_json(nodes))
        result = analyzer.get_az_distribution()
        assert result["us-east-1a"] == 2
        assert result["us-east-1b"] == 1


# =============================================================================
# get_high_pod_count_nodes TESTS
# =============================================================================


class TestGetHighPodCountNodes:
    """Tests for DistributionAnalyzer.get_high_pod_count_nodes()."""

    def test_empty_nodes(self) -> None:
        """Test with no nodes."""
        analyzer = DistributionAnalyzer(_make_nodes_json([]))
        result = analyzer.get_high_pod_count_nodes()
        assert result == []

    def test_node_above_threshold(self) -> None:
        """Test detection of node above pod capacity threshold."""
        nodes = [_make_node(name="busy-node", max_pods="10")]
        pods = [_make_pod(f"pod-{i}", "busy-node") for i in range(9)]
        analyzer = DistributionAnalyzer(_make_nodes_json(nodes), _make_pods_json(pods))
        result = analyzer.get_high_pod_count_nodes(threshold_pct=80.0)
        assert len(result) == 1
        assert result[0]["name"] == "busy-node"
        assert result[0]["pod_count"] == 9
        assert result[0]["pod_pct"] == 90.0

    def test_node_below_threshold(self) -> None:
        """Test that nodes below threshold are excluded."""
        nodes = [_make_node(name="idle-node", max_pods="100")]
        pods = [_make_pod("pod-1", "idle-node")]
        analyzer = DistributionAnalyzer(_make_nodes_json(nodes), _make_pods_json(pods))
        result = analyzer.get_high_pod_count_nodes(threshold_pct=80.0)
        assert result == []


# =============================================================================
# get_all_distributions TESTS
# =============================================================================


class TestGetAllDistributions:
    """Tests for DistributionAnalyzer.get_all_distributions()."""

    def test_returns_all_keys(self) -> None:
        """Test that get_all_distributions returns all expected keys."""
        analyzer = DistributionAnalyzer(_make_nodes_json([]))
        result = analyzer.get_all_distributions()
        expected_keys = {
            "node_conditions",
            "node_taints",
            "kubelet_versions",
            "instance_types",
            "availability_zones",
            "node_groups_az_matrix",
            "high_pod_nodes",
        }
        assert set(result.keys()) == expected_keys


# =============================================================================
# pods_by_node PROPERTY TESTS
# =============================================================================


class TestPodsByNode:
    """Tests for DistributionAnalyzer.pods_by_node property."""

    def test_empty_pods(self) -> None:
        """Test pods_by_node with no pods."""
        analyzer = DistributionAnalyzer(_make_nodes_json([]))
        assert analyzer.pods_by_node == {}

    def test_pods_grouped_by_node(self) -> None:
        """Test pods_by_node groups pods correctly by node name."""
        nodes = [_make_node(name="n1"), _make_node(name="n2")]
        pods = [
            _make_pod("p1", "n1"),
            _make_pod("p2", "n1"),
            _make_pod("p3", "n2"),
        ]
        analyzer = DistributionAnalyzer(_make_nodes_json(nodes), _make_pods_json(pods))
        result = analyzer.pods_by_node
        assert len(result["n1"]) == 2
        assert len(result["n2"]) == 1

    def test_pods_by_node_caching(self) -> None:
        """Test that pods_by_node is cached (same result on second access)."""
        pods = [_make_pod("p1", "n1")]
        analyzer = DistributionAnalyzer(_make_nodes_json([]), _make_pods_json(pods))
        result1 = analyzer.pods_by_node
        result2 = analyzer.pods_by_node
        assert result1 is result2
