"""Tests for pod parser."""

from __future__ import annotations

import pytest

from kubeagle.controllers.cluster.parsers.pod_parser import PodParser


class TestPodParser:
    """Tests for PodParser class."""

    @pytest.fixture
    def parser(self) -> PodParser:
        """Create PodParser instance."""
        return PodParser()

    def test_parser_init(self, parser: PodParser) -> None:
        """Test PodParser initialization."""
        assert isinstance(parser, PodParser)

    def test_parse_pod_requests_empty(self, parser: PodParser) -> None:
        """Test parse_pod_requests with empty pods list."""
        pods: list[dict] = []

        result = parser.parse_pod_requests(pods)

        assert "cpu_stats" in result
        assert "memory_stats" in result
        assert "cpu_request_stats" in result
        assert "memory_request_stats" in result
        assert "cpu_limit_stats" in result
        assert "memory_limit_stats" in result
        assert result["cpu_stats"]["min"] == 0
        assert result["cpu_stats"]["avg"] == 0.0
        assert result["cpu_stats"]["max"] == 0
        assert result["cpu_stats"]["p95"] == 0
        assert result["memory_stats"]["min"] == 0
        assert result["cpu_limit_stats"]["min"] == 0
        assert result["memory_limit_stats"]["min"] == 0

    def test_parse_pod_requests_single_pod(self, parser: PodParser) -> None:
        """Test parse_pod_requests with single running pod."""
        pods = [
            {
                "spec": {
                    "nodeName": "node1",
                    "containers": [
                        {
                            "name": "main",
                            "resources": {
                                "requests": {"cpu": "100m", "memory": "128Mi"},
                            },
                        }
                    ],
                },
                "status": {"phase": "Running"},
            }
        ]

        result = parser.parse_pod_requests(pods)

        assert result["cpu_stats"]["min"] > 0
        assert result["cpu_stats"]["max"] > 0
        assert result["memory_stats"]["min"] > 0

    def test_parse_pod_requests_multiple_containers(self, parser: PodParser) -> None:
        """Test parse_pod_requests with multiple containers per pod."""
        pods = [
            {
                "spec": {
                    "nodeName": "node1",
                    "containers": [
                        {
                            "name": "main",
                            "resources": {
                                "requests": {"cpu": "100m", "memory": "128Mi"},
                            },
                        },
                        {
                            "name": "sidecar",
                            "resources": {
                                "requests": {"cpu": "50m", "memory": "64Mi"},
                            },
                        },
                    ],
                },
                "status": {"phase": "Running"},
            }
        ]

        result = parser.parse_pod_requests(pods)

        # Should sum resources from both containers (100 + 50 = 150 millicores)
        assert result["cpu_stats"]["min"] > 100

    def test_parse_pod_requests_includes_limit_statistics(self, parser: PodParser) -> None:
        """Test parse_pod_requests returns min/avg/max/p95 for limits."""
        pods = [
            {
                "spec": {
                    "nodeName": "node1",
                    "containers": [
                        {
                            "name": "main",
                            "resources": {
                                "requests": {"cpu": "100m", "memory": "128Mi"},
                                "limits": {"cpu": "400m", "memory": "512Mi"},
                            },
                        }
                    ],
                },
                "status": {"phase": "Running"},
            },
            {
                "spec": {
                    "nodeName": "node2",
                    "containers": [
                        {
                            "name": "main",
                            "resources": {
                                "requests": {"cpu": "200m", "memory": "256Mi"},
                                "limits": {"cpu": "800m", "memory": "1Gi"},
                            },
                        }
                    ],
                },
                "status": {"phase": "Running"},
            },
        ]

        result = parser.parse_pod_requests(pods)

        assert result["cpu_limit_stats"]["min"] == 400.0
        assert result["cpu_limit_stats"]["max"] == 800.0
        assert result["memory_limit_stats"]["min"] == 512 * 1024 * 1024
        assert result["memory_limit_stats"]["max"] == 1024 * 1024 * 1024

    def test_parse_pod_requests_no_resources(self, parser: PodParser) -> None:
        """Test parse_pod_requests with pods that have no resources defined."""
        pods = [
            {
                "spec": {
                    "nodeName": "node1",
                    "containers": [
                        {
                            "name": "main",
                        }
                    ],
                },
                "status": {"phase": "Running"},
            }
        ]

        result = parser.parse_pod_requests(pods)

        # No resources means 0 requests, so stats should be empty
        assert result["cpu_stats"]["min"] == 0
        assert result["memory_stats"]["min"] == 0

    def test_parse_distribution_empty(self, parser: PodParser) -> None:
        """Test parse_distribution with empty nodes and pods."""
        nodes: list[dict] = []
        pods: list[dict] = []

        result = parser.parse_distribution(nodes, pods)

        assert result.total_pods == 0
        assert result.min_pods_per_node == 0
        assert result.max_pods_per_node == 0
        assert result.avg_pods_per_node == 0.0

    def test_parse_distribution_with_nodes(self, parser: PodParser) -> None:
        """Test parse_distribution calculates distribution."""
        nodes = [
            {
                "metadata": {
                    "name": "node1",
                    "labels": {"eks.amazonaws.com/nodegroup": "worker"},
                },
            },
            {
                "metadata": {
                    "name": "node2",
                    "labels": {"eks.amazonaws.com/nodegroup": "worker"},
                },
            },
        ]
        pods = [
            {
                "spec": {"nodeName": "node1"},
                "status": {"phase": "Running"},
            },
            {
                "spec": {"nodeName": "node2"},
                "status": {"phase": "Running"},
            },
        ]

        result = parser.parse_distribution(nodes, pods)

        assert result.total_pods == 2
        assert result.min_pods_per_node == 1
        assert result.max_pods_per_node == 1
        # high_pod_nodes should have entries for both nodes
        assert len(result.high_pod_nodes) == 2

    def test_parse_distribution_groups_by_node_group(self, parser: PodParser) -> None:
        """Test parse_distribution groups pods by node group."""
        nodes = [
            {
                "metadata": {
                    "name": "node1",
                    "labels": {"eks.amazonaws.com/nodegroup": "spot"},
                },
            },
            {
                "metadata": {
                    "name": "node2",
                    "labels": {"eks.amazonaws.com/nodegroup": "ondemand"},
                },
            },
        ]
        pods = [
            {"spec": {"nodeName": "node1"}, "status": {"phase": "Running"}},
            {"spec": {"nodeName": "node1"}, "status": {"phase": "Running"}},
            {"spec": {"nodeName": "node2"}, "status": {"phase": "Running"}},
        ]

        result = parser.parse_distribution(nodes, pods)

        assert result.by_node_group["spot"]["total_pods"] == 2
        assert result.by_node_group["ondemand"]["total_pods"] == 1

    def test_parse_distribution_ignores_pending_pods(self, parser: PodParser) -> None:
        """Test parse_distribution only counts Running/Pending pods that are on a node."""
        nodes = [{"metadata": {"name": "node1", "labels": {}}}]
        pods = [
            {"spec": {"nodeName": "node1"}, "status": {"phase": "Running"}},
            {"spec": {"nodeName": "node1"}, "status": {"phase": "Pending"}},
            {"spec": {"nodeName": "node1"}, "status": {"phase": "Succeeded"}},
        ]

        result = parser.parse_distribution(nodes, pods)

        # parse_pods_by_node includes Running and Pending, not Succeeded
        assert result.total_pods == 2

    def test_parse_distribution_handles_unknown_node(self, parser: PodParser) -> None:
        """Test parse_distribution handles pods on unknown nodes."""
        nodes = [{"metadata": {"name": "node1", "labels": {}}}]
        pods = [
            {"spec": {"nodeName": "node1"}, "status": {"phase": "Running"}},
            {"spec": {"nodeName": "unknown-node"}, "status": {"phase": "Running"}},
        ]

        result = parser.parse_distribution(nodes, pods)

        # Only 1 pod counted in node stats (node1), unknown-node not in nodes list
        # Total pods from parse_pods_by_node includes both, but distribution
        # only iterates known nodes
        assert result.total_pods == 1  # Only pods on known nodes counted
