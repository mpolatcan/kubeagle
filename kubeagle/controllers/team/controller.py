"""Team controller for team-related operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from kubeagle.controllers.base import BaseController
from kubeagle.controllers.team.fetchers import TeamFetcher
from kubeagle.controllers.team.mappers import TeamMapper
from kubeagle.controllers.team.parsers import TeamParser


class TeamController(BaseController):
    """Team-related operations using CODEOWNERS file."""

    def __init__(self, codeowners_path: Path | None = None) -> None:
        """Initialize the team controller.

        Args:
            codeowners_path: Optional path to CODEOWNERS file.
        """
        super().__init__()
        self._codeowners_path = codeowners_path
        self._team_fetcher = TeamFetcher(codeowners_path)
        self._team_mapper = TeamMapper(codeowners_path)
        self._team_parser = TeamParser()

    async def check_connection(self) -> bool:
        """Check if the CODEOWNERS file is accessible.

        Returns:
            True if accessible, False otherwise.
        """
        if self._codeowners_path is None:
            return False
        return self._codeowners_path.exists()

    async def fetch_all(self) -> dict[str, Any]:
        """Fetch all team data.

        Returns:
            Dictionary with team data.
        """
        return {
            "teams": self._team_fetcher.get_all_teams(),
            "team_mapping": self._team_mapper.to_dict(),
        }

    async def load_teams(self) -> list[str]:
        """Load teams from CODEOWNERS file.

        Returns:
            List of team names.
        """
        if self._codeowners_path is not None:
            self._team_fetcher.load_codeowners(self._codeowners_path)
        return self._team_fetcher.get_all_teams()

    def get_team_for_path(self, chart_path: Path) -> str | None:
        """Get team name for a chart path.

        Args:
            chart_path: Path to chart directory

        Returns:
            Team name or None if not found.
        """
        return self._team_mapper.get_team_for_path(chart_path)

    def get_team(self, chart_name: str) -> str:
        """Get team name for a chart by name.

        Args:
            chart_name: Name of the chart

        Returns:
            Team name or "Unknown" if not found.
        """
        return self._team_mapper.get_team(chart_name)

    def get_all_teams(self) -> list[str]:
        """Get list of all unique team names.

        Returns:
            Sorted list of team names.
        """
        return self._team_mapper.get_all_teams()

    def get_teams_with_charts(self) -> dict[str, list[str]]:
        """Get mapping of teams to their charts.

        Returns:
            Dictionary mapping team names to list of chart names.
        """
        return self._team_mapper.get_teams_with_charts()

    def find_team_info(self, team_name: str) -> list[Any]:
        """Find all TeamInfo entries for a given team name.

        Args:
            team_name: Name of the team to find

        Returns:
            List of TeamInfo entries for the team.
        """
        return self._team_mapper.find_team_info(team_name)

    def find_charts_for_team(self, team_name: str) -> list[str]:
        """Find all chart names/patterns owned by a team.

        Args:
            team_name: Name of the team

        Returns:
            List of chart patterns owned by the team.
        """
        return self._team_mapper.find_charts_for_team(team_name)

    def get_team_owners(self, team_name: str) -> list[str]:
        """Get all owners for a team.

        Args:
            team_name: Name of the team

        Returns:
            List of unique owner references for the team.
        """
        return self._team_mapper.get_team_owners(team_name)

    def has_team(self, team_name: str) -> bool:
        """Check if a team exists in the mapping.

        Args:
            team_name: Name of the team to check

        Returns:
            True if team exists, False otherwise.
        """
        return self._team_mapper.has_team(team_name)

    def search_by_owner(self, owner_pattern: str) -> list[Any]:
        """Find all teams that have an owner matching the pattern.

        Args:
            owner_pattern: Pattern to match owners

        Returns:
            List of TeamInfo entries with matching owners.
        """
        return self._team_mapper.search_by_owner(owner_pattern)

    def group_charts_by_team(
        self, charts: list[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        """Group charts by team name.

        Args:
            charts: List of chart dictionaries

        Returns:
            Dictionary mapping team name to list of charts.
        """
        return self._team_parser.group_charts_by_team(charts)

    def to_dict(self) -> dict[str, Any]:
        """Export team mapping as a dictionary.

        Returns:
            Dictionary representation of the team mapping.
        """
        return self._team_mapper.to_dict()
