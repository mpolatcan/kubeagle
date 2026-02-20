"""Tests for team controller."""

from __future__ import annotations

from pathlib import Path

import pytest

from kubeagle.controllers.team.controller import TeamController


class TestTeamController:
    """Tests for TeamController class."""

    @pytest.fixture
    def controller(self, tmp_path: Path) -> TeamController:
        """Create TeamController instance."""
        return TeamController(codeowners_path=tmp_path / "CODEOWNERS")

    def test_controller_init(self, controller: TeamController) -> None:
        """Test TeamController initialization."""
        assert controller._codeowners_path is not None

    def test_controller_init_no_path(self) -> None:
        """Test TeamController with no CODEOWNERS path."""
        controller = TeamController()
        assert controller._codeowners_path is None

    @pytest.mark.asyncio
    async def test_check_connection_exists(self, controller: TeamController, tmp_path: Path) -> None:
        """Test check_connection returns True when CODEOWNERS exists."""
        codeowners = tmp_path / "CODEOWNERS"
        codeowners.write_text("* @team")
        controller = TeamController(codeowners_path=codeowners)

        result = await controller.check_connection()

        assert result is True

    @pytest.mark.asyncio
    async def test_check_connection_not_exists(self, controller: TeamController) -> None:
        """Test check_connection returns False when CODEOWNERS doesn't exist."""
        controller = TeamController(codeowners_path=Path("/nonexistent/CODEOWNERS"))

        result = await controller.check_connection()

        assert result is False

    @pytest.mark.asyncio
    async def test_check_connection_no_path(self) -> None:
        """Test check_connection returns False when no path is set."""
        controller = TeamController()

        result = await controller.check_connection()

        assert result is False

    @pytest.mark.asyncio
    async def test_fetch_all(self, controller: TeamController) -> None:
        """Test fetch_all returns team data."""
        result = await controller.fetch_all()

        assert isinstance(result, dict)
        assert "teams" in result
        assert "team_mapping" in result

    @pytest.mark.asyncio
    async def test_load_teams_with_path(self, controller: TeamController, tmp_path: Path) -> None:
        """Test load_teams loads teams from CODEOWNERS."""
        codeowners = tmp_path / "CODEOWNERS"
        codeowners.write_text("* @team-a\n/charts/* @team-b")
        controller = TeamController(codeowners_path=codeowners)

        result = await controller.load_teams()

        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_load_teams_no_path(self, controller: TeamController) -> None:
        """Test load_teams returns empty list when no path set."""
        controller = TeamController()

        result = await controller.load_teams()

        assert result == []
