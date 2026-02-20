"""Tests for team parser."""

from __future__ import annotations

import pytest

from kubeagle.controllers.team.parsers.team_parser import TeamParser


class TestTeamParser:
    """Tests for TeamParser class."""

    @pytest.fixture
    def parser(self) -> TeamParser:
        """Create TeamParser instance."""
        return TeamParser()

    def test_parser_init(self, parser: TeamParser) -> None:
        """Test TeamParser initialization."""
        assert isinstance(parser, TeamParser)

    def test_parse_team_statistics_empty(self, parser: TeamParser) -> None:
        """Test parse_team_statistics with empty charts list."""
        result = parser.parse_team_statistics("team-a", [])

        assert result.team_name == "team-a"
        assert result.chart_count == 0
        assert result.cpu_request == 0.0
        assert result.cpu_limit == 0.0

    def test_parse_team_statistics_single_chart(self, parser: TeamParser) -> None:
        """Test parse_team_statistics with single chart."""
        charts = [
            {
                "cpu_request": 100,
                "cpu_limit": 200,
                "memory_request": 128,
                "memory_limit": 256,
                "has_anti_affinity": True,
                "has_topology_spread": False,
                "has_liveness": True,
                "has_readiness": True,
            }
        ]

        result = parser.parse_team_statistics("team-a", charts)

        assert result.team_name == "team-a"
        assert result.chart_count == 1
        assert result.cpu_request == 100
        assert result.cpu_limit == 200
        assert result.avg_cpu_ratio == 2.0

    def test_parse_team_statistics_multiple_charts(self, parser: TeamParser) -> None:
        """Test parse_team_statistics with multiple charts."""
        charts = [
            {
                "cpu_request": 100,
                "cpu_limit": 200,
                "memory_request": 128,
                "memory_limit": 256,
                "has_anti_affinity": True,
                "has_topology_spread": True,
                "has_liveness": True,
                "has_readiness": True,
            },
            {
                "cpu_request": 200,
                "cpu_limit": 600,
                "memory_request": 256,
                "memory_limit": 512,
                "has_anti_affinity": False,
                "has_topology_spread": False,
                "has_liveness": False,
                "has_readiness": False,
            },
        ]

        result = parser.parse_team_statistics("team-a", charts, violation_count=3)

        assert result.chart_count == 2
        assert result.cpu_request == 300
        # Avg CPU ratio: (2.0 + 3.0) / 2 = 2.5
        assert result.avg_cpu_ratio == 2.5
        assert result.violation_count == 3
        assert result.has_anti_affinity is True  # OR across all charts
        assert result.has_topology is True  # OR across all charts

    def test_parse_team_statistics_calculates_averages(self, parser: TeamParser) -> None:
        """Test parse_team_statistics calculates correct averages."""
        charts = [
            {
                "cpu_request": 100,
                "cpu_limit": 200,  # ratio = 2.0
                "memory_request": 128,
                "memory_limit": 256,  # ratio = 2.0
                "has_anti_affinity": False,
                "has_topology_spread": False,
                "has_liveness": False,
                "has_readiness": False,
            },
            {
                "cpu_request": 200,
                "cpu_limit": 800,  # ratio = 4.0
                "memory_request": 256,
                "memory_limit": 1024,  # ratio = 4.0
                "has_anti_affinity": False,
                "has_topology_spread": False,
                "has_liveness": False,
                "has_readiness": False,
            },
        ]

        result = parser.parse_team_statistics("team-a", charts)

        # Expected average ratio is 3.0.
        assert result.avg_cpu_ratio == 3.0
        # Expected average ratio is 3.0.
        assert result.avg_memory_ratio == 3.0

    def test_parse_team_statistics_handles_missing_resources(self, parser: TeamParser) -> None:
        """Test parse_team_statistics handles charts with missing resources."""
        charts = [
            {
                "cpu_request": 0,
                "cpu_limit": 0,
                "memory_request": 0,
                "memory_limit": 0,
                "has_anti_affinity": False,
                "has_topology_spread": False,
                "has_liveness": False,
                "has_readiness": False,
            },
        ]

        result = parser.parse_team_statistics("team-a", charts)

        assert result.avg_cpu_ratio == 0.0
        assert result.avg_memory_ratio == 0.0

    def test_group_charts_by_team_empty(self, parser: TeamParser) -> None:
        """Test group_charts_by_team with empty list."""
        result = parser.group_charts_by_team([])

        assert result == {}

    def test_group_charts_by_team_single_team(self, parser: TeamParser) -> None:
        """Test group_charts_by_team groups by team."""
        charts = [
            {"name": "chart1", "team": "team-a"},
            {"name": "chart2", "team": "team-a"},
            {"name": "chart3", "team": "team-b"},
        ]

        result = parser.group_charts_by_team(charts)

        assert "team-a" in result
        assert "team-b" in result
        assert len(result["team-a"]) == 2
        assert len(result["team-b"]) == 1

    def test_group_charts_by_team_unknown_team(self, parser: TeamParser) -> None:
        """Test group_charts_by_team handles unknown teams."""
        charts = [
            {"name": "chart1"},  # No team key
            {"name": "chart2", "team": "team-a"},
        ]

        result = parser.group_charts_by_team(charts)

        assert "Unknown" in result
        assert len(result["Unknown"]) == 1
        assert len(result["team-a"]) == 1
