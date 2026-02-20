"""Tests for team mapper."""

from __future__ import annotations

from pathlib import Path

import pytest

from kubeagle.controllers.team.mappers.team_mapper import TeamMapper


class TestTeamMapper:
    """Tests for TeamMapper class."""

    @pytest.fixture
    def mapper(self, tmp_path: Path) -> TeamMapper:
        """Create TeamMapper instance."""
        return TeamMapper(codeowners_path=tmp_path / "CODEOWNERS")

    def test_mapper_init(self, mapper: TeamMapper) -> None:
        """Test TeamMapper initialization."""
        assert mapper._codeowners_path is not None

    def test_mapper_init_no_path(self) -> None:
        """Test TeamMapper with no path."""
        mapper = TeamMapper()
        assert mapper._codeowners_path is None

    def test_get_team_for_path_no_path(self) -> None:
        """Test get_team_for_path returns None when no path set."""
        mapper = TeamMapper()

        result = mapper.get_team_for_path(Path("/some/path"))

        assert result is None

    def test_get_team_no_mapping(self, mapper: TeamMapper) -> None:
        """Test get_team returns Unknown when no mapping exists."""
        result = mapper.get_team("unknown-chart")

        assert result == "Unknown"

    def test_get_all_teams_empty(self, mapper: TeamMapper) -> None:
        """Test get_all_teams returns empty list when no teams."""
        result = mapper.get_all_teams()

        assert result == []

    def test_has_team_false(self, mapper: TeamMapper) -> None:
        """Test has_team returns False for unknown team."""
        result = mapper.has_team("unknown-team")

        assert result is False

    def test_to_dict_empty(self, mapper: TeamMapper) -> None:
        """Test to_dict returns dict with empty teams and mapping when no data loaded."""
        result = mapper.to_dict()

        assert result == {"teams": [], "team_mapping": {}}

    def test_register_chart_team_normalizes_and_stores_mapping(self) -> None:
        """Test values-based fallback team is normalized and mapped."""
        mapper = TeamMapper()

        result = mapper.register_chart_team("my-chart", "platform_team")

        assert result == "Platform-Team"
        assert mapper.get_team("my-chart") == "Platform-Team"
        assert mapper.to_dict()["team_mapping"]["my-chart"] == "Platform-Team"

    def test_register_chart_team_keeps_existing_known_mapping(self) -> None:
        """Test register_chart_team does not overwrite existing non-unknown mapping."""
        mapper = TeamMapper()
        mapper.team_mapping["my-chart"] = "Backend"

        result = mapper.register_chart_team("my-chart", "platform_team")

        assert result == "Backend"
        assert mapper.get_team("my-chart") == "Backend"

    def test_resolve_chart_team_uses_alternate_values_file(self, tmp_path: Path) -> None:
        """Test resolver finds team from another values file type when current lacks it."""
        chart_path = tmp_path / "my-chart"
        chart_path.mkdir()

        current_values_file = chart_path / "values-automation.yaml"
        current_values_file.write_text("replicaCount: 2\n")
        (chart_path / "values.yaml").write_text(
            "global:\n  labels:\n    project_team: platform_team\n",
            encoding="utf-8",
        )

        mapper = TeamMapper()
        result = mapper.resolve_chart_team(
            chart_name="my-chart",
            values={"replicaCount": 2},
            chart_path=chart_path,
            values_file=current_values_file,
        )

        assert result == "Platform-Team"
        assert mapper.get_team("my-chart") == "Platform-Team"

    def test_resolve_chart_team_falls_back_to_codeowners(self, tmp_path: Path) -> None:
        """Test resolver falls back to CODEOWNERS when no values team exists."""
        codeowners = tmp_path / "CODEOWNERS"
        codeowners.write_text("/my-chart/ @org/backend\n", encoding="utf-8")

        mapper = TeamMapper(codeowners_path=codeowners)
        result = mapper.resolve_chart_team(
            chart_name="my-chart",
            values={},
            chart_path=tmp_path / "my-chart",
        )

        assert result == "Backend"

    def test_resolve_chart_team_infers_from_unanimous_siblings(
        self, tmp_path: Path
    ) -> None:
        """Test resolver infers unknown chart team from unanimous sibling ownership."""
        charts_parent = tmp_path / "service-group"
        chart_a = charts_parent / "chart-a"
        chart_b = charts_parent / "chart-b"
        chart_c = charts_parent / "chart-c"
        chart_a.mkdir(parents=True)
        chart_b.mkdir()
        chart_c.mkdir()

        for chart in (chart_a, chart_b, chart_c):
            (chart / "Chart.yaml").write_text("apiVersion: v2\nname: demo\n", encoding="utf-8")

        (chart_b / "values.yaml").write_text(
            "global:\n  labels:\n    project_team: platform_team\n",
            encoding="utf-8",
        )
        (chart_c / "values.yaml").write_text(
            "global:\n  labels:\n    project_team: platform_team\n",
            encoding="utf-8",
        )

        mapper = TeamMapper()
        result = mapper.resolve_chart_team(
            chart_name="chart-a",
            values={"replicaCount": 1},
            chart_path=chart_a,
            values_file=chart_a / "values-automation.yaml",
        )

        assert result == "Platform-Team"
        assert mapper.get_team("chart-a") == "Platform-Team"

    def test_resolve_chart_team_does_not_infer_when_siblings_mixed(
        self, tmp_path: Path
    ) -> None:
        """Test resolver keeps Unknown when sibling teams are not unanimous."""
        charts_parent = tmp_path / "service-group"
        chart_a = charts_parent / "chart-a"
        chart_b = charts_parent / "chart-b"
        chart_c = charts_parent / "chart-c"
        chart_a.mkdir(parents=True)
        chart_b.mkdir()
        chart_c.mkdir()

        for chart in (chart_a, chart_b, chart_c):
            (chart / "Chart.yaml").write_text("apiVersion: v2\nname: demo\n", encoding="utf-8")

        (chart_b / "values.yaml").write_text(
            "global:\n  labels:\n    project_team: platform_team\n",
            encoding="utf-8",
        )
        (chart_c / "values.yaml").write_text(
            "global:\n  labels:\n    project_team: backend_team\n",
            encoding="utf-8",
        )

        mapper = TeamMapper()
        result = mapper.resolve_chart_team(
            chart_name="chart-a",
            values={"replicaCount": 1},
            chart_path=chart_a,
            values_file=chart_a / "values-automation.yaml",
        )

        assert result == "Unknown"
