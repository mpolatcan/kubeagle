"""Team parser for parsing team-related data."""

from __future__ import annotations

from typing import Any

from kubeagle.models.teams.team_statistics import TeamStatistics


class TeamParser:
    """Parses team-related data into structured formats."""

    def __init__(self) -> None:
        """Initialize team parser."""
        pass

    def parse_team_statistics(
        self,
        team_name: str,
        charts: list[dict[str, Any]],
        violation_count: int = 0,
    ) -> TeamStatistics:
        """Parse team statistics from charts.

        Args:
            team_name: Name of the team
            charts: List of chart dictionaries
            violation_count: Number of violations for this team

        Returns:
            TeamStatistics object.
        """
        cpu_req = cpu_lim = mem_req = mem_lim = 0.0
        cpu_ratios: list[float] = []
        mem_ratios: list[float] = []
        has_aa = has_topo = has_probes = False

        for chart in charts:
            cpu_req += chart.get("cpu_request", 0)
            cpu_lim += chart.get("cpu_limit", 0)
            mem_req += chart.get("memory_request", 0)
            mem_lim += chart.get("memory_limit", 0)

            cpu_request = chart.get("cpu_request", 0)
            cpu_limit = chart.get("cpu_limit", 0)
            mem_request = chart.get("memory_request", 0)
            mem_limit = chart.get("memory_limit", 0)

            if cpu_request > 0 and cpu_limit > 0:
                cpu_ratios.append(cpu_limit / cpu_request)
            if mem_request > 0 and mem_limit > 0:
                mem_ratios.append(mem_limit / mem_request)

            has_aa = has_aa or chart.get("has_anti_affinity", False)
            has_topo = has_topo or chart.get("has_topology_spread", False)
            has_probes = has_probes or (
                chart.get("has_liveness", False) or chart.get("has_readiness", False)
            )

        avg_cpu_ratio = sum(cpu_ratios) / len(cpu_ratios) if cpu_ratios else 0.0
        avg_mem_ratio = sum(mem_ratios) / len(mem_ratios) if mem_ratios else 0.0

        return TeamStatistics(
            team_name=team_name,
            chart_count=len(charts),
            cpu_request=cpu_req,
            cpu_limit=cpu_lim,
            memory_request=mem_req,
            memory_limit=mem_lim,
            avg_cpu_ratio=avg_cpu_ratio,
            avg_memory_ratio=avg_mem_ratio,
            has_anti_affinity=has_aa,
            has_topology=has_topo,
            has_probes=has_probes,
            violation_count=violation_count,
        )

    def group_charts_by_team(
        self, charts: list[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        """Group charts by team name.

        Args:
            charts: List of chart dictionaries

        Returns:
            Dictionary mapping team name to list of charts.
        """
        by_team: dict[str, list[dict[str, Any]]] = {}
        for chart in charts:
            team = chart.get("team", "Unknown")
            if team not in by_team:
                by_team[team] = []
            by_team[team].append(chart)
        return by_team
