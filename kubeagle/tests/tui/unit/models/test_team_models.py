"""Tests for team models."""

from __future__ import annotations

from kubeagle.models.teams.distribution import PodDistributionInfo
from kubeagle.models.teams.team_info import TeamInfo
from kubeagle.models.teams.team_statistics import TeamStatistics


class TestTeamInfo:
    """Tests for TeamInfo model."""

    def test_team_info_creation(self) -> None:
        """Test TeamInfo creation."""
        team = TeamInfo(
            name="my-team",
            pattern="* @my-team",
            owners=["@team/my-team"],
        )

        assert team.name == "my-team"
        assert len(team.owners) == 1
        assert team.team_ref is None


class TestTeamStatistics:
    """Tests for TeamStatistics model."""

    def test_team_statistics_creation(self) -> None:
        """Test TeamStatistics creation."""
        stats = TeamStatistics(
            team_name="my-team",
            chart_count=5,
            cpu_request=500.0,
            cpu_limit=1000.0,
            memory_request=640.0,
            memory_limit=1280.0,
            avg_cpu_ratio=2.0,
            avg_memory_ratio=2.0,
            has_anti_affinity=True,
            has_topology=True,
            has_probes=True,
            violation_count=3,
        )

        assert stats.team_name == "my-team"
        assert stats.chart_count == 5
        assert stats.cpu_request == 500.0
        assert stats.has_anti_affinity is True


class TestPodDistributionInfo:
    """Tests for PodDistributionInfo model."""

    def test_pod_distribution_info_creation(self) -> None:
        """Test PodDistributionInfo creation."""
        dist = PodDistributionInfo(
            total_pods=50,
            min_pods_per_node=5,
            max_pods_per_node=20,
            avg_pods_per_node=10.0,
            p95_pods_per_node=18.0,
            high_pod_nodes=[{"name": "node1", "pod_count": 20}],
            by_node_group={"worker": {"total": 50, "nodes": 5}},
        )

        assert dist.total_pods == 50
        assert dist.min_pods_per_node == 5
        assert len(dist.high_pod_nodes) == 1
