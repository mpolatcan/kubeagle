"""Tests for team fetcher."""

from __future__ import annotations

from pathlib import Path

import pytest

from kubeagle.controllers.team.fetchers.team_fetcher import TeamFetcher


class TestTeamFetcher:
    """Tests for TeamFetcher class."""

    @pytest.fixture
    def fetcher(self, tmp_path: Path) -> TeamFetcher:
        """Create TeamFetcher instance."""
        return TeamFetcher(codeowners_path=tmp_path / "CODEOWNERS")

    def test_fetcher_init(self, fetcher: TeamFetcher) -> None:
        """Test TeamFetcher initialization."""
        assert fetcher.codeowners_path is not None

    def test_fetcher_init_no_path(self) -> None:
        """Test TeamFetcher with no path."""
        fetcher = TeamFetcher()
        assert fetcher.codeowners_path is None

    def test_load_codeowners(self, fetcher: TeamFetcher, tmp_path: Path) -> None:
        """Test load_codeowners parses CODEOWNERS file."""
        codeowners = tmp_path / "CODEOWNERS"
        codeowners.write_text("* @team-alpha\n/charts/* @team-beta")

        fetcher.load_codeowners(codeowners)

        assert len(fetcher.teams) > 0

    def test_get_all_teams_empty(self, fetcher: TeamFetcher) -> None:
        """Test get_all_teams returns empty list when no teams loaded."""
        result = fetcher.get_all_teams()
        assert result == []
