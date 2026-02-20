"""Tests for chart parser."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from kubeagle.constants.enums import QoSClass
from kubeagle.controllers.charts.parsers.chart_parser import ChartParser


class TestChartParser:
    """Tests for ChartParser class."""

    @pytest.fixture
    def parser(self) -> ChartParser:
        """Create ChartParser instance."""
        return ChartParser()

    def test_parser_init(self, parser: ChartParser) -> None:
        """Test ChartParser initialization."""
        assert parser.team_mapper is None

    def test_parse_cpu_from_dict(self, parser: ChartParser) -> None:
        """Test _parse_cpu extracts CPU from values."""
        values = {
            "resources": {
                "requests": {"cpu": "100m"},
                "limits": {"cpu": "500m"},
            }
        }
        cpu_request = parser._parse_cpu(values, "requests", "cpu")
        cpu_limit = parser._parse_cpu(values, "limits", "cpu")
        assert cpu_request == 100.0  # 100m = 100 millicores
        assert cpu_limit == 500.0  # 500m = 500 millicores

    def test_parse_cpu_from_dict_missing(self, parser: ChartParser) -> None:
        """Test _parse_cpu returns 0 for missing values."""
        values = {"resources": {"requests": {}}}
        result = parser._parse_cpu(values, "requests", "cpu")
        assert result == 0.0

    def test_parse_memory_from_dict(self, parser: ChartParser) -> None:
        """Test _parse_memory extracts memory from values."""
        values = {
            "resources": {
                "requests": {"memory": "128Mi"},
                "limits": {"memory": "256Mi"},
            }
        }
        result = parser._parse_memory(values, "requests", "memory")
        # Result is in bytes
        assert result > 0

    def test_extract_team_from_global_labels_project_team(
        self, parser: ChartParser
    ) -> None:
        """Test _extract_team extracts global.labels.project_team value."""
        values = {"global": {"labels": {"project_team": "my-team"}}}
        result = parser._extract_team(values)
        assert result == "my-team"

    def test_extract_team_from_project_team(self, parser: ChartParser) -> None:
        """Test _extract_team extracts project_team from values."""
        values = {"project_team": "platform_team"}
        result = parser._extract_team(values)
        assert result == "platform_team"

    def test_extract_team_from_annotations(self, parser: ChartParser) -> None:
        """Test _extract_team extracts team from annotations."""
        values = {"annotations": {"team": "my-team"}}
        result = parser._extract_team(values)
        assert result == "my-team"

    def test_extract_team_from_labels(self, parser: ChartParser) -> None:
        """Test _extract_team extracts team from labels."""
        values = {"labels": {"team": "my-team"}}
        result = parser._extract_team(values)
        assert result == "my-team"

    def test_extract_team_unknown(self, parser: ChartParser) -> None:
        """Test _extract_team returns Unknown when not found."""
        values = {"key": "value"}
        result = parser._extract_team(values)
        assert result == "Unknown"

    def test_extract_team_from_mapper(self) -> None:
        """Test _extract_team prefers TeamMapper when available."""

        class MapperStub:
            def get_team(self, chart_name: str) -> str:
                return "platform-team" if chart_name == "my-chart" else "Unknown"

        parser = ChartParser(team_mapper=MapperStub())
        result = parser._extract_team({}, chart_name="my-chart")
        assert result == "platform-team"

    def test_extract_team_uses_mapper_resolver_when_available(self, tmp_path: Path) -> None:
        """Test _extract_team delegates to TeamMapper resolver when available."""

        class MapperStub:
            def __init__(self) -> None:
                self.calls: list[tuple[str, str | None, str | None]] = []

            def resolve_chart_team(
                self,
                chart_name: str,
                values: dict[str, object] | None = None,
                chart_path: Path | None = None,
                values_file: Path | None = None,
            ) -> str:
                chart_path_str = str(chart_path) if chart_path else None
                values_file_str = str(values_file) if values_file else None
                self.calls.append((chart_name, chart_path_str, values_file_str))
                return "Platform-Team"

        mapper = MapperStub()
        parser = ChartParser(team_mapper=mapper)
        chart_path = tmp_path / "my-chart"
        values_file = chart_path / "values.yaml"

        result = parser._extract_team(
            {"global": {"labels": {"project_team": "my-team"}}},
            chart_name="my-chart",
            chart_path=chart_path,
            values_file=values_file,
        )

        assert result == "Platform-Team"
        assert mapper.calls == [("my-chart", str(chart_path), str(values_file))]

    def test_extract_team_mapper_uses_values_when_present(self) -> None:
        """Test _extract_team prefers values source over mapper result."""

        class MapperStub:
            def get_team(self, chart_name: str) -> str:
                return "platform-team"

        parser = ChartParser(team_mapper=MapperStub())
        values = {"global": {"labels": {"project_team": "my-team"}}}
        result = parser._extract_team(values, chart_name="my-chart")
        assert result == "my-team"

    def test_extract_team_mapper_fallback_when_values_missing(self) -> None:
        """Test _extract_team falls back to mapper when values key is missing."""

        class MapperStub:
            def get_team(self, chart_name: str) -> str:
                return "platform-team"

        parser = ChartParser(team_mapper=MapperStub())
        result = parser._extract_team({}, chart_name="my-chart")
        assert result == "platform-team"

    def test_extract_team_mapper_registers_project_team_fallback(self) -> None:
        """Test _extract_team registers project_team in mapper-compatible format."""

        class MapperStub:
            def __init__(self) -> None:
                self.register_calls: list[tuple[str, str]] = []

            def get_team(self, chart_name: str) -> str:
                return "Unknown"

            def register_chart_team(self, chart_name: str, team_name: str) -> str:
                self.register_calls.append((chart_name, team_name))
                return "Platform-Team"

        mapper = MapperStub()
        parser = ChartParser(team_mapper=mapper)
        result = parser._extract_team(
            {"global": {"labels": {"project_team": "platform_team"}}},
            chart_name="my-chart",
        )
        assert result == "Platform-Team"
        assert mapper.register_calls == [("my-chart", "platform_team")]

    def test_determine_qos_guaranteed(self, parser: ChartParser) -> None:
        """Test _determine_qos returns GUARANTEED when all limits match requests."""
        result = parser._determine_qos(100, 100, 128, 128)
        assert result == QoSClass.GUARANTEED

    def test_determine_qos_burstable(self, parser: ChartParser) -> None:
        """Test _determine_qos returns BURSTABLE when limits differ from requests."""
        result = parser._determine_qos(100, 500, 128, 256)
        assert result == QoSClass.BURSTABLE

    def test_determine_qos_best_effort(self, parser: ChartParser) -> None:
        """Test _determine_qos returns BEST_EFFORT when no requests/limits."""
        result = parser._determine_qos(0, 0, 0, 0)
        assert result == QoSClass.BEST_EFFORT

    def test_has_probe_true(self, parser: ChartParser) -> None:
        """Test _has_probe returns True when probe exists."""
        values = {"livenessProbe": {"httpGet": {"path": "/"}}}
        result = parser._has_probe(values, "livenessProbe")
        assert result is True

    def test_has_probe_false(self, parser: ChartParser) -> None:
        """Test _has_probe returns False when probe doesn't exist."""
        values = {"key": "value"}
        result = parser._has_probe(values, "livenessProbe")
        assert result is False

    def test_has_anti_affinity_true(self, parser: ChartParser) -> None:
        """Test _has_anti_affinity returns True when configured."""
        values = {"affinity": {"podAntiAffinity": {}}}
        result = parser._has_anti_affinity(values)
        assert result is True

    def test_has_anti_affinity_false(self, parser: ChartParser) -> None:
        """Test _has_anti_affinity returns False when not configured."""
        values = {"affinity": {"podAffinity": {}}}
        result = parser._has_anti_affinity(values)
        assert result is False

    def test_has_topology_spread_true(self, parser: ChartParser) -> None:
        """Test _has_topology_spread returns True when configured."""
        values = {"topologySpreadConstraints": [{"maxSkew": 1}]}
        result = parser._has_topology_spread(values)
        assert result is True

    def test_has_topology_spread_false(self, parser: ChartParser) -> None:
        """Test _has_topology_spread returns False when not configured."""
        values = {"key": "value"}
        result = parser._has_topology_spread(values)
        assert result is False

    def test_has_pdb_enabled(self, parser: ChartParser) -> None:
        """Test _has_pdb returns True when PDB is enabled."""
        values = {"pdb": {"enabled": True, "minAvailable": 1}}
        result = parser._has_pdb(values)
        assert result is True

    def test_has_pdb_disabled(self, parser: ChartParser) -> None:
        """Test _has_pdb returns False when PDB is disabled."""
        values = {"pdb": {"enabled": False}}
        result = parser._has_pdb(values)
        assert result is False

    def test_has_pdb_not_configured(self, parser: ChartParser) -> None:
        """Test _has_pdb returns False when PDB not configured."""
        values = {"key": "value"}
        result = parser._has_pdb(values)
        assert result is False

    def test_get_pdb_values(self, parser: ChartParser) -> None:
        """Test _get_pdb_values extracts PDB values."""
        values = {"pdb": {"minAvailable": 1, "maxUnavailable": 2}}
        result = parser._get_pdb_values(values)
        assert result == (1, 2)

    def test_get_pdb_values_string_conversion(self, parser: ChartParser) -> None:
        """Test _get_pdb_values converts string values to int."""
        values = {"pdb": {"minAvailable": "3", "maxUnavailable": "4"}}
        result = parser._get_pdb_values(values)
        assert result == (3, 4)

    def test_get_pdb_values_invalid_string(self, parser: ChartParser) -> None:
        """Test _get_pdb_values handles invalid string values."""
        values = {"pdb": {"minAvailable": "invalid", "maxUnavailable": "invalid"}}
        result = parser._get_pdb_values(values)
        assert result == (None, None)

    def test_get_replicas(self, parser: ChartParser) -> None:
        """Test _get_replicas extracts replica count."""
        values = {"replicaCount": 3}
        result = parser._get_replicas(values)
        assert result == 3

    def test_get_replicas_fallback(self, parser: ChartParser) -> None:
        """Test _get_replicas falls back to replicas key."""
        values = {"replicas": 5}
        result = parser._get_replicas(values)
        assert result == 5

    def test_get_replicas_not_int(self, parser: ChartParser) -> None:
        """Test _get_replicas returns None when value is not int."""
        values = {"replicaCount": "3"}
        result = parser._get_replicas(values)
        assert result is None

    def test_get_priority_class(self, parser: ChartParser) -> None:
        """Test _get_priority_class extracts priority class."""
        values = {"priorityClassName": "high-priority"}
        result = parser._get_priority_class(values)
        assert result == "high-priority"

    def test_get_priority_class_not_set(self, parser: ChartParser) -> None:
        """Test _get_priority_class returns None when not set."""
        values = {"key": "value"}
        result = parser._get_priority_class(values)
        assert result is None

    def test_parse_full_chart(self, parser: ChartParser, tmp_path: Path) -> None:
        """Test parse creates complete ChartInfo."""
        chart_path = tmp_path / "my-chart"
        chart_path.mkdir()
        (chart_path / "Chart.yaml").write_text("name: metadata-name\n")

        values_file = chart_path / "values.yaml"
        values = {
            "global": {"labels": {"project_team": "my-team"}},
            "replicaCount": 2,
            "resources": {
                "requests": {"cpu": "100m", "memory": "128Mi"},
                "limits": {"cpu": "500m", "memory": "512Mi"},
            },
            "livenessProbe": {"httpGet": {"path": "/"}},
            "readinessProbe": {"httpGet": {"path": "/"}},
            "affinity": {"podAntiAffinity": {}},
            "topologySpreadConstraints": [{"maxSkew": 1}],
            "pdb": {"enabled": True, "minAvailable": 1},
        }
        values_file.write_text(yaml.dump(values))

        result = parser.parse(chart_path, values, values_file)

        assert result.name == "metadata-name"
        assert result.team == "my-team"
        assert result.values_file == str(values_file)
        assert result.cpu_request > 0
        assert result.cpu_limit > 0
        assert result.qos_class == QoSClass.BURSTABLE
        assert result.has_liveness is True
        assert result.has_readiness is True
        assert result.has_anti_affinity is True
        assert result.has_topology_spread is True
        assert result.pdb_enabled is True
        assert result.replicas == 2

    def test_parse_uses_path_name_when_chart_yaml_is_invalid(
        self, parser: ChartParser, tmp_path: Path
    ) -> None:
        """Invalid Chart.yaml should fall back to legacy path-based name resolution."""
        chart_path = tmp_path / "fallback-chart"
        chart_path.mkdir()
        (chart_path / "Chart.yaml").write_text("name: [invalid\n")

        values_file = chart_path / "values.yaml"
        values_file.write_text("key: value")

        result = parser.parse(chart_path, {"key": "value"}, values_file)
        assert result.name == "fallback-chart"

    def test_parse_minimal_chart(self, parser: ChartParser, tmp_path: Path) -> None:
        """Test parse handles minimal chart values."""
        chart_path = tmp_path / "minimal-chart"
        chart_path.mkdir()

        values_file = chart_path / "values.yaml"
        values_file.write_text("key: value")

        result = parser.parse(chart_path, {"key": "value"}, values_file)

        assert result.team == "Unknown"
        assert result.cpu_request == 0.0
        assert result.cpu_limit == 0.0
        assert result.qos_class == QoSClass.BEST_EFFORT
        assert result.has_liveness is False
        assert result.has_anti_affinity is False

    def test_parse_main_chart_uses_parent_name(
        self, parser: ChartParser, tmp_path: Path
    ) -> None:
        """Missing metadata falls back to mapping `<service>/main` to service chart name."""
        chart_path = tmp_path / "contact-service" / "main"
        chart_path.mkdir(parents=True)

        values_file = chart_path / "values.yaml"
        values = {"global": {"labels": {"project_team": "platform"}}}
        values_file.write_text(yaml.dump(values))

        result = parser.parse(chart_path, values, values_file)
        assert result.name == "contact-service"
