"""Chart parser for parsing Helm chart data."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from kubeagle.constants.enums import QoSClass
from kubeagle.models.charts.chart_info import ChartInfo
from kubeagle.utils.resource_parser import (
    parse_cpu_from_dict,
    parse_memory_from_dict,
)

logger = logging.getLogger(__name__)


class ChartParser:
    """Parses Helm chart values and extracts relevant information."""

    def __init__(self, team_mapper: Any | None = None) -> None:
        """Initialize chart parser.

        Args:
            team_mapper: Optional team mapper for CODEOWNERS-based team detection.
        """
        self.team_mapper = team_mapper

    def _parse_cpu(
        self, values: dict[str, Any], container_type: str, resource: str
    ) -> float:
        """Parse CPU value in millicores from values dict.

        Args:
            values: Parsed values dictionary
            container_type: Container type (e.g., "requests", "limits")
            resource: Resource name (e.g., "cpu")

        Returns:
            CPU value in millicores.
        """
        return parse_cpu_from_dict(values, container_type, resource)

    def _parse_memory(
        self, values: dict[str, Any], container_type: str, resource: str
    ) -> float:
        """Parse memory value in bytes from values dict.

        Args:
            values: Parsed values dictionary
            container_type: Container type (e.g., "requests", "limits")
            resource: Resource name (e.g., "memory")

        Returns:
            Memory value in bytes.
        """
        return parse_memory_from_dict(values, container_type, resource)

    def parse(
        self, chart_path: Path, values: dict[str, Any], values_file: Path
    ) -> ChartInfo:
        """Parse a chart's values file and extract chart information.

        Args:
            chart_path: Path to chart directory
            values: Parsed values dictionary
            values_file: Path to values file used

        Returns:
            ChartInfo object with parsed data.
        """
        chart_name = self._resolve_chart_name(chart_path)

        # Extract team - first try CODEOWNERS via TeamMapper, then values.yaml
        team = self._extract_team(
            values,
            chart_name=chart_name,
            chart_path=chart_path,
            values_file=values_file,
        )

        # Parse resources
        cpu_request = parse_cpu_from_dict(values, "requests", "cpu")
        cpu_limit = parse_cpu_from_dict(values, "limits", "cpu")
        memory_request = parse_memory_from_dict(values, "requests", "memory")
        memory_limit = parse_memory_from_dict(values, "limits", "memory")

        # Determine QoS class
        qos_class = self._determine_qos(
            cpu_request, cpu_limit, memory_request, memory_limit
        )

        # Check for probes
        has_liveness = self._has_probe(values, "livenessProbe")
        has_readiness = self._has_probe(values, "readinessProbe")
        has_startup = self._has_probe(values, "startupProbe")

        # Also check nested probes structure
        if not has_liveness or not has_readiness or not has_startup:
            probes = values.get("probes", {})
            if not has_liveness:
                has_liveness = bool(probes.get("liveness"))
            if not has_readiness:
                has_readiness = bool(probes.get("readiness"))
            if not has_startup:
                has_startup = bool(probes.get("startup"))

        # Check for anti-affinity
        has_anti_affinity = self._has_anti_affinity(values)
        has_topology_spread = self._has_topology_spread(values)

        # Check PDB
        pdb_enabled = self._has_pdb(values)
        pdb_template_exists = self._has_pdb_template(chart_path)
        pdb_min_available, pdb_max_unavailable = self._get_pdb_values(values)

        # Get replicas
        replicas = self._get_replicas(values)

        # Get priority class
        priority_class = self._get_priority_class(values)

        # Umbrella chart detection and resource aggregation
        sub_chart_aliases = self._identify_umbrella_sub_charts(chart_path, values)
        is_umbrella = len(sub_chart_aliases) > 0
        sub_chart_count = len(sub_chart_aliases)

        if is_umbrella:
            cpu_request, cpu_limit, memory_request, memory_limit, replicas = (
                self._aggregate_sub_chart_resources(
                    values, sub_chart_aliases,
                    cpu_request, cpu_limit, memory_request, memory_limit, replicas,
                )
            )
            qos_class = self._determine_qos(
                cpu_request, cpu_limit, memory_request, memory_limit,
            )

        return ChartInfo(
            name=chart_name,
            team=team,
            values_file=str(values_file),
            cpu_request=cpu_request,
            cpu_limit=cpu_limit,
            memory_request=memory_request,
            memory_limit=memory_limit,
            qos_class=qos_class,
            has_liveness=has_liveness,
            has_readiness=has_readiness,
            has_startup=has_startup,
            has_anti_affinity=has_anti_affinity,
            has_topology_spread=has_topology_spread,
            has_topology=has_topology_spread,
            pdb_enabled=pdb_enabled,
            pdb_template_exists=pdb_template_exists,
            pdb_min_available=pdb_min_available,
            pdb_max_unavailable=pdb_max_unavailable,
            replicas=replicas,
            priority_class=priority_class,
            is_umbrella=is_umbrella,
            sub_chart_count=sub_chart_count,
        )

    def _resolve_chart_name(self, chart_path: Path) -> str:
        """Resolve chart display/release name from chart metadata or directory path."""
        chart_name_from_yaml = self._read_chart_name_from_yaml(chart_path)
        if chart_name_from_yaml is not None:
            return chart_name_from_yaml

        return self._resolve_chart_name_from_path(chart_path)

    @staticmethod
    def _read_chart_name_from_yaml(chart_path: Path) -> str | None:
        """Read chart name from Chart.yaml metadata."""
        chart_yaml_path = chart_path / "Chart.yaml"
        if not chart_yaml_path.is_file():
            return None

        try:
            with open(chart_yaml_path, encoding="utf-8") as handle:
                content = yaml.safe_load(handle)
        except (OSError, yaml.YAMLError):
            return None

        if not isinstance(content, dict):
            return None

        raw_name = content.get("name")
        if raw_name is None:
            return None

        chart_name = str(raw_name).strip()
        return chart_name or None

    @staticmethod
    def _resolve_chart_name_from_path(chart_path: Path) -> str:
        """Legacy path-based chart name resolution fallback."""
        if chart_path.name == "main" and chart_path.parent.name:
            return chart_path.parent.name
        return chart_path.name

    def _extract_team(
        self,
        values: dict[str, Any],
        chart_name: str | None = None,
        chart_path: Path | None = None,
        values_file: Path | None = None,
    ) -> str:
        """Extract team name from values content first, then CODEOWNERS mapper."""
        if self.team_mapper is not None and chart_name:
            resolve_chart_team = getattr(self.team_mapper, "resolve_chart_team", None)
            if callable(resolve_chart_team):
                return str(
                    resolve_chart_team(
                        chart_name=chart_name,
                        values=values,
                        chart_path=chart_path,
                        values_file=values_file,
                    )
                )

        team = self._extract_team_from_values(values)
        if team is not None:
            if self.team_mapper is not None and chart_name:
                register_mapping = getattr(self.team_mapper, "register_chart_team", None)
                if callable(register_mapping):
                    return str(register_mapping(chart_name, team))

            return team

        if self.team_mapper is not None and chart_name:
            mapped_team = self.team_mapper.get_team(chart_name)
            if mapped_team != "Unknown":
                return mapped_team

        return "Unknown"

    def _extract_team_from_values(self, values: dict[str, Any]) -> str | None:
        """Extract team value from known values.yaml team fields."""
        team_paths: list[list[str]] = [
            ["global", "labels", "project_team"],
            ["project_team"],
            ["global", "project_team"],
            ["helm", "global", "project_team"],
            ["team"],
            ["annotations", "team"],
            ["labels", "team"],
        ]

        for path in team_paths:
            current: Any = values
            found = True
            for key in path:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    found = False
                    break
            if not found or current is None:
                continue

            team = str(current).strip()
            if team:
                return team

        return None

    def _determine_qos(
        self, cpu_req: float, cpu_lim: float, mem_req: float, mem_lim: float
    ) -> QoSClass:
        """Determine QoS class based on resource requests/limits."""
        if cpu_req > 0 and cpu_lim > 0 and mem_req > 0 and mem_lim > 0:
            if cpu_req == cpu_lim and mem_req == mem_lim:
                return QoSClass.GUARANTEED
            return QoSClass.BURSTABLE
        return QoSClass.BEST_EFFORT

    def _has_probe(self, values: dict[str, Any], probe_name: str) -> bool:
        """Check if container has a specific probe."""
        return probe_name in values

    def _has_anti_affinity(self, values: dict[str, Any]) -> bool:
        """Check if pod anti-affinity is configured."""
        affinity = values.get("affinity", {})
        if not affinity:
            return False
        return affinity.get("podAntiAffinity") is not None

    def _has_topology_spread(self, values: dict[str, Any]) -> bool:
        """Check if topology spread constraints are configured."""
        topology = values.get("topologySpreadConstraints", [])
        return len(topology) > 0

    def _has_pdb(self, values: dict[str, Any]) -> bool:
        """Check if PDB is enabled."""
        pdb = values.get("pdb", {})
        if not pdb:
            return False
        return pdb.get("enabled", False)

    def _has_pdb_template(self, chart_path: Path) -> bool:
        """Check if chart has a PDB template file."""
        pdb_template_path = chart_path / "templates" / "pdb.yaml"
        return pdb_template_path.exists()

    def _get_pdb_values(self, values: dict[str, Any]) -> tuple[int | None, int | None]:
        """Extract PDB minAvailable and maxUnavailable values from values."""
        pdb = values.get("pdb", {})
        min_available: int | None = pdb.get("minAvailable")
        max_unavailable: int | None = pdb.get("maxUnavailable")

        # Convert string to int if needed
        if isinstance(min_available, str):
            try:
                min_available = int(min_available)
            except ValueError:
                min_available = None
        if isinstance(max_unavailable, str):
            try:
                max_unavailable = int(max_unavailable)
            except ValueError:
                max_unavailable = None

        return min_available, max_unavailable

    def _get_replicas(self, values: dict[str, Any]) -> int | None:
        """Get replica count."""
        replica_count = values.get("replicaCount")
        if replica_count is None:
            replica_count = values.get("replicas")
        return replica_count if isinstance(replica_count, int) else None

    def _get_priority_class(self, values: dict[str, Any]) -> str | None:
        """Get priority class name."""
        return values.get("priorityClassName")

    # -----------------------------------------------------------------
    # Umbrella chart detection and aggregation
    # -----------------------------------------------------------------

    def _identify_umbrella_sub_charts(
        self,
        chart_path: Path,
        values: dict[str, Any],
    ) -> list[str]:
        """Identify sub-charts of a local umbrella chart.

        A dependency is a true sub-chart if:
        1. It has a ``file://`` repository reference in Chart.yaml
        2. The referenced directory exists on disk
        3. The dependency alias appears as a top-level key in values
        4. That key contains workload definitions (resources or replicaCount)

        Returns list of alias names for identified sub-charts.
        """
        local_deps = self._detect_local_file_dependencies(chart_path)
        if not local_deps:
            return []

        sub_chart_aliases: list[str] = []
        for dep in local_deps:
            alias = dep["alias"]
            repository = dep["repository"]

            if self._resolve_dependency_path(chart_path, repository) is None:
                continue

            sub_values = values.get(alias)
            if not isinstance(sub_values, dict):
                continue

            if self._has_workload_resources(sub_values):
                sub_chart_aliases.append(alias)

        return sub_chart_aliases

    @staticmethod
    def _detect_local_file_dependencies(
        chart_path: Path,
    ) -> list[dict[str, str]]:
        """Parse Chart.yaml and return dependencies with ``file://`` repositories."""
        chart_yaml_path = chart_path / "Chart.yaml"
        if not chart_yaml_path.is_file():
            return []

        try:
            with open(chart_yaml_path, encoding="utf-8") as fh:
                content = yaml.safe_load(fh)
        except (OSError, yaml.YAMLError):
            return []

        if not isinstance(content, dict):
            return []

        dependencies = content.get("dependencies", [])
        if not isinstance(dependencies, list):
            return []

        local_deps: list[dict[str, str]] = []
        for dep in dependencies:
            if not isinstance(dep, dict):
                continue
            repo = dep.get("repository", "")
            if not isinstance(repo, str) or not repo.startswith("file://"):
                continue
            name = str(dep.get("name", "")).strip()
            alias = str(dep.get("alias", "") or name).strip()
            if not alias:
                continue
            local_deps.append({
                "name": name,
                "alias": alias,
                "repository": repo,
            })

        return local_deps

    @staticmethod
    def _resolve_dependency_path(
        chart_path: Path,
        repository: str,
    ) -> Path | None:
        """Resolve a ``file://`` repository URL to an absolute path.

        Only returns a path for dependencies that live within the chart's
        own project folder.  For charts at the repo root (e.g.
        ``analytics-api/``) the project root is ``chart_path`` itself.
        For the ``main/`` pattern (e.g. ``contact-service/main/``) the
        project root is the parent (``contact-service/``).

        Shared infrastructure charts referenced via ``file://../insider-redis``
        resolve outside the project boundary and are excluded so they are not
        double-counted as sub-chart rows.

        Returns the resolved Path if it is a valid sub-chart directory,
        else None.
        """
        relative = repository.removeprefix("file://").rstrip("/")
        resolved = (chart_path / relative).resolve()
        if not resolved.is_dir():
            return None

        # Determine project root: for ``main/`` charts use the parent.
        project_root = chart_path.resolve()
        if chart_path.name == "main":
            project_root = project_root.parent

        # Dependency must live under the project root to be a true sub-chart.
        try:
            resolved.relative_to(project_root)
        except ValueError:
            return None

        return resolved

    @staticmethod
    def _has_workload_resources(sub_values: dict[str, Any]) -> bool:
        """Return True if *sub_values* contains workload resource definitions.

        Checks for ``resources.requests``/``resources.limits``, or
        ``replicaCount``/``replicas``.  This distinguishes real sub-chart
        workloads from shared library configs (e.g. parameter-store).
        """
        if "replicaCount" in sub_values or "replicas" in sub_values:
            return True

        resources = sub_values.get("resources")
        if isinstance(resources, dict):
            if "requests" in resources or "limits" in resources:
                return True
            default = resources.get("default")
            if isinstance(default, dict) and (
                "requests" in default or "limits" in default
            ):
                return True

        return False

    def expand_umbrella_sub_charts(
        self,
        parent: ChartInfo,
        values: dict[str, Any],
        sub_chart_aliases: list[str],
        chart_path: Path | None = None,
    ) -> list[ChartInfo]:
        """Create individual ChartInfo objects for each sub-chart of an umbrella.

        Resource resolution follows a fallback chain:
        ``root values.yaml[alias]`` → ``subchart_dir/values.yaml``.

        The second step (sub-chart own values.yaml) is only available
        in local mode where ``chart_path`` is provided.

        Args:
            parent: The umbrella parent ChartInfo.
            values: Full parsed values dictionary (root values.yaml).
            sub_chart_aliases: List of detected sub-chart alias keys.
            chart_path: Chart directory for resolving sub-chart own
                values.yaml (local mode only).

        Returns:
            List of ChartInfo objects, one per sub-chart.
        """
        # Pre-load sub-chart own values.yaml files for fallback
        sub_chart_defaults = self._load_sub_chart_defaults(
            chart_path, sub_chart_aliases,
        ) if chart_path is not None else {}

        sub_charts: list[ChartInfo] = []

        for alias in sub_chart_aliases:
            sub_values = values.get(alias)
            if not isinstance(sub_values, dict):
                continue

            cpu_request = parse_cpu_from_dict(sub_values, "requests", "cpu")
            cpu_limit = parse_cpu_from_dict(sub_values, "limits", "cpu")
            memory_request = parse_memory_from_dict(sub_values, "requests", "memory")
            memory_limit = parse_memory_from_dict(sub_values, "limits", "memory")

            # Fallback: if root values.yaml has no resources, use sub-chart own values.yaml
            if cpu_request == 0 and cpu_limit == 0 and memory_request == 0 and memory_limit == 0:
                defaults = sub_chart_defaults.get(alias)
                if defaults is not None:
                    cpu_request = parse_cpu_from_dict(defaults, "requests", "cpu")
                    cpu_limit = parse_cpu_from_dict(defaults, "limits", "cpu")
                    memory_request = parse_memory_from_dict(defaults, "requests", "memory")
                    memory_limit = parse_memory_from_dict(defaults, "limits", "memory")

            qos_class = self._determine_qos(
                cpu_request, cpu_limit, memory_request, memory_limit,
            )

            replicas = self._get_replicas(sub_values)

            has_liveness = self._has_probe(sub_values, "livenessProbe")
            has_readiness = self._has_probe(sub_values, "readinessProbe")
            has_startup = self._has_probe(sub_values, "startupProbe")
            if not has_liveness or not has_readiness or not has_startup:
                probes = sub_values.get("probes", {})
                if not has_liveness:
                    has_liveness = bool(probes.get("liveness"))
                if not has_readiness:
                    has_readiness = bool(probes.get("readiness"))
                if not has_startup:
                    has_startup = bool(probes.get("startup"))

            has_anti_affinity = self._has_anti_affinity(sub_values)
            has_topology_spread = self._has_topology_spread(sub_values)
            pdb_enabled = self._has_pdb(sub_values)
            pdb_min_available, pdb_max_unavailable = self._get_pdb_values(sub_values)
            priority_class = self._get_priority_class(sub_values)

            sub_charts.append(
                ChartInfo(
                    name=alias,
                    team=parent.team,
                    values_file=parent.values_file,
                    namespace=parent.namespace,
                    cpu_request=cpu_request,
                    cpu_limit=cpu_limit,
                    memory_request=memory_request,
                    memory_limit=memory_limit,
                    qos_class=qos_class,
                    has_liveness=has_liveness,
                    has_readiness=has_readiness,
                    has_startup=has_startup,
                    has_anti_affinity=has_anti_affinity,
                    has_topology_spread=has_topology_spread,
                    has_topology=has_topology_spread,
                    pdb_enabled=pdb_enabled,
                    pdb_template_exists=False,
                    pdb_min_available=pdb_min_available,
                    pdb_max_unavailable=pdb_max_unavailable,
                    replicas=replicas,
                    priority_class=priority_class,
                    parent_chart=parent.name,
                )
            )

        return sub_charts

    def _load_sub_chart_defaults(
        self,
        chart_path: Path,
        sub_chart_aliases: list[str],
    ) -> dict[str, dict[str, Any]]:
        """Load sub-chart own values.yaml files for the fallback chain.

        Returns a mapping of alias → parsed values dict for sub-charts
        whose dependency directory contains a values.yaml file.
        """
        local_deps = self._detect_local_file_dependencies(chart_path)
        dep_path_map: dict[str, Path] = {}
        for dep in local_deps:
            resolved = self._resolve_dependency_path(chart_path, dep["repository"])
            if resolved is not None:
                dep_path_map[dep["alias"]] = resolved

        defaults: dict[str, dict[str, Any]] = {}
        for alias in sub_chart_aliases:
            dep_dir = dep_path_map.get(alias)
            if dep_dir is None:
                continue
            vf = dep_dir / "values.yaml"
            if not vf.is_file():
                continue
            try:
                with open(vf, encoding="utf-8") as fh:
                    content = yaml.safe_load(fh)
                if isinstance(content, dict):
                    defaults[alias] = content
            except (OSError, yaml.YAMLError):
                pass

        return defaults

    def _aggregate_sub_chart_resources(
        self,
        values: dict[str, Any],
        sub_chart_aliases: list[str],
        base_cpu_request: float,
        base_cpu_limit: float,
        base_memory_request: float,
        base_memory_limit: float,
        base_replicas: int | None,
    ) -> tuple[float, float, float, float, int | None]:
        """Sum resource values from sub-chart sections in *values*.

        Each sub-chart's ``resources`` and ``replicaCount`` are added on top
        of the parent's base values.
        """
        total_cpu_req = base_cpu_request
        total_cpu_lim = base_cpu_limit
        total_mem_req = base_memory_request
        total_mem_lim = base_memory_limit
        total_replicas = base_replicas or 0
        has_any_replicas = base_replicas is not None

        for alias in sub_chart_aliases:
            sub = values.get(alias)
            if not isinstance(sub, dict):
                continue

            total_cpu_req += parse_cpu_from_dict(sub, "requests", "cpu")
            total_cpu_lim += parse_cpu_from_dict(sub, "limits", "cpu")
            total_mem_req += parse_memory_from_dict(sub, "requests", "memory")
            total_mem_lim += parse_memory_from_dict(sub, "limits", "memory")

            sub_replicas = sub.get("replicaCount")
            if sub_replicas is None:
                sub_replicas = sub.get("replicas")
            if isinstance(sub_replicas, int):
                total_replicas += sub_replicas
                has_any_replicas = True

        return (
            total_cpu_req,
            total_cpu_lim,
            total_mem_req,
            total_mem_lim,
            total_replicas if has_any_replicas else None,
        )
