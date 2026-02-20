"""Cluster screen presenter - data loading, state management, and data formatting."""

from __future__ import annotations

import asyncio
import logging
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from textual.message import Message
from textual.worker import get_current_worker

from kubeagle.constants.timeouts import CLUSTER_CHECK_TIMEOUT
from kubeagle.controllers import ClusterController
from kubeagle.models.events.event_summary import EventSummary
from kubeagle.screens.cluster.config import (
    MAX_EVENTS_DISPLAY,
    NODE_GROUPS_TABLE_COLUMNS,
    NODE_TABLE_COLUMNS,
)
from kubeagle.utils.cluster_summary import (
    count_blocking_pdbs,
    summarize_nodes,
)

if TYPE_CHECKING:
    from kubeagle.models.events.event_info import EventDetail
    from kubeagle.models.teams.distribution import PodDistributionInfo

logger = logging.getLogger(__name__)


# =============================================================================
# Worker Messages
# =============================================================================


class ClusterSourceLoaded(Message):
    """Message indicating a single data source has been loaded incrementally."""

    def __init__(self, key: str) -> None:
        super().__init__()
        self.key = key


class ClusterDataLoaded(Message):
    """Message indicating all cluster data has been loaded."""


class ClusterDataLoadFailed(Message):
    """Message indicating cluster data loading failed."""

    def __init__(self, error: str) -> None:
        super().__init__()
        self.error = error


@dataclass(frozen=True)
class _SourceSpec:
    """Definition for a single cluster data source fetch."""

    key: str
    loader: Callable[[], Awaitable[Any]]
    default: Any


class ClusterPresenter:
    """Presenter for ClusterScreen - handles data loading, state, and formatting."""

    _AWS_AZ_SPLIT_RE = re.compile(r"^([a-z]{2}(?:-[a-z0-9]+)+-\d+)([a-z])$")
    _DEFAULT_EVENT_WINDOW_HOURS = 0.25  # 15 minutes (align with Home default)
    _MAX_PARALLEL_SOURCES = 4
    _PROGRESS_ACTIVE_SOURCE_LIMIT = 3
    _PROGRESS_SOURCE_LABELS: dict[str, str] = {
        "nodes": "Nodes",
        "events": "Events",
        "event_summary": "Event summary",
        "pdbs": "PDB coverage",
        "single_replica": "Single replica",
        "all_workloads": "Workloads",
        "charts_overview": "Charts overview",
        "pod_distribution": "Pod distribution",
        "critical_events": "Critical events",
        "node_groups": "Node groups",
        "pod_request_stats": "Pod request stats",
        "high_pod_count_nodes": "High pod nodes",
        "az_distribution": "AZ distribution",
        "instance_type_distribution": "Instance types",
        "kubelet_version_distribution": "Kubelet versions",
        "node_groups_az_matrix": "Node group AZ matrix",
        "node_conditions": "Node conditions",
        "node_taints": "Node taints",
    }
    _NODE_NAME_MAX_LENGTH = NODE_TABLE_COLUMNS[0][1]
    _PARTIAL_SOURCE_EMIT_INTERVAL_SECONDS = 0.35
    _PARTIAL_NODE_DERIVED_EMIT_INTERVAL_SECONDS = 0.75
    _ERROR_PENALTY_PER_EVENT = 5.0
    _ERROR_PENALTY_CAP = 40.0
    _WARNING_PENALTY_PER_EVENT = 1.0
    _WARNING_PENALTY_CAP = 25.0
    _BLOCKING_PENALTY_PER_EVENT = 10.0
    _BLOCKING_PENALTY_CAP = 40.0
    _CONNECTION_CHECK_ATTEMPTS = 2
    _CONNECTION_CHECK_RETRY_DELAY_SECONDS = 1.0
    _CONNECTION_CHECK_TIMEOUT_SECONDS = CLUSTER_CHECK_TIMEOUT

    def __init__(self, screen: Any) -> None:
        self._screen = screen
        self._data: dict[str, Any] = {}
        self._is_loading = False
        self._force_refresh_next_load = False
        self._error_message = ""
        self._partial_errors: dict[str, str] = {}  # key -> user-friendly error message
        self._loaded_keys: set[str] = set()  # tracks which data keys have arrived
        self._event_window_hours = self._DEFAULT_EVENT_WINDOW_HOURS
        self._last_partial_emit_at: dict[str, float] = {}
        self._last_node_derived_emit_at = 0.0

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def is_loading(self) -> bool:
        return self._is_loading

    @property
    def error_message(self) -> str:
        return self._error_message

    @property
    def partial_errors(self) -> dict[str, str]:
        """Per-data-source error messages (key -> user-friendly message)."""
        return self._partial_errors

    @property
    def loaded_keys(self) -> set[str]:
        """Keys that have completed loading (success or fallback on error)."""
        return set(self._loaded_keys)

    @property
    def is_connected(self) -> bool:
        return bool(self._data.get("cluster_name"))

    @property
    def event_window_hours(self) -> float:
        """Current event lookback window used for event sources."""
        return self._event_window_hours

    def set_event_window_hours(self, hours: float) -> None:
        """Set runtime event lookback window for future refreshes."""
        if hours <= 0:
            self._event_window_hours = self._DEFAULT_EVENT_WINDOW_HOURS
            return
        self._event_window_hours = hours

    # =========================================================================
    # Data Accessors
    # =========================================================================

    def get_cluster_name(self) -> str:
        return self._data.get("cluster_name", "Unknown")

    def get_source_value(self, key: str) -> Any:
        """Return raw source payload for UI overlay decisions."""
        return self._data.get(key)

    def get_nodes(self) -> list:
        return self._data.get("nodes", [])

    def get_events(self) -> list:
        return self._data.get("events", [])

    def get_single_replica(self) -> list:
        return self._data.get("single_replica", [])

    def get_pdbs(self) -> list:
        return self._data.get("pdbs", [])

    def get_node_resources(self) -> list:
        return self._data.get("node_resources", [])

    def get_node_groups(self) -> dict:
        return self._data.get("node_groups", {})

    def get_all_workloads(self) -> list:
        return self._data.get("all_workloads", [])

    def get_charts_overview(self) -> dict[str, Any]:
        return self._data.get("charts_overview", self._default_charts_overview())

    def get_event_summary(self) -> EventSummary | None:
        return self._data.get("event_summary")

    def get_pod_request_stats(self) -> dict:
        return self._data.get("pod_request_stats", {})

    def get_az_distribution(self) -> dict[str, int]:
        return self._data.get("az_distribution", {})

    def get_instance_type_distribution(self) -> dict[str, int]:
        return self._data.get("instance_type_distribution", {})

    def get_kubelet_version_distribution(self) -> dict[str, int]:
        return self._data.get("kubelet_version_distribution", {})

    def get_node_groups_az_matrix(self) -> dict[str, dict[str, int]]:
        return self._data.get("node_groups_az_matrix", {})

    def get_pod_distribution(self) -> PodDistributionInfo | None:
        return self._data.get("pod_distribution")

    def get_critical_events(self) -> list[EventDetail]:
        return self._data.get("critical_events", [])

    def get_node_conditions(self) -> dict[str, dict[str, int]]:
        return self._data.get("node_conditions", {})

    def get_node_taints(self) -> dict[str, Any]:
        return self._data.get("node_taints", {})

    def get_high_pod_count_nodes(self) -> list[dict[str, Any]]:
        return self._data.get("high_pod_count_nodes", [])

    # =========================================================================
    # Data Loading
    # =========================================================================

    def load_data(self, *, force_refresh: bool = False) -> None:
        """Start loading cluster data."""
        if force_refresh:
            self._force_refresh_next_load = True
        self._is_loading = True
        self._error_message = ""
        start_worker = getattr(self._screen, "start_worker", None)
        if callable(start_worker):
            start_worker(self._load_cluster_data_worker, name="cluster-data", exclusive=True)
            return
        self._screen.run_worker(
            self._load_cluster_data_worker, name="cluster-data", exclusive=True
        )

    @staticmethod
    def _friendly_error(error: BaseException) -> str:
        """Convert an exception to a user-friendly error message."""
        msg = str(error)
        if "timed out" in msg.lower() or "timeout" in msg.lower():
            return "Connection timed out"
        if "connection refused" in msg.lower():
            return "Connection refused"
        if "not found" in msg.lower():
            return "Resource not found"
        # Strip raw command arrays from error messages
        if "Command [" in msg or "Command '" in msg:
            if "timed out" in msg:
                return "Command timed out"
            return "Command failed"
        # Truncate long messages
        if len(msg) > 80:
            return msg[:77] + "..."
        return msg or "Unknown error"

    def _store_result(self, key: str, result: Any, default: Any = None) -> None:
        """Store a gather result, tracking errors for partial failures."""
        if isinstance(result, BaseException):
            friendly = self._friendly_error(result)
            self._partial_errors[key] = friendly
            logger.warning("Failed to load %s: %s", key, result)
            # Store default value so accessors return safe empties
            if default is None:
                _dict_keys = ("node_groups", "pod_request_stats", "node_conditions", "node_taints", "az_distribution", "instance_type_distribution", "kubelet_version_distribution", "node_groups_az_matrix")
                _none_keys = ("event_summary", "pod_distribution")
                if key in _none_keys:
                    default = None
                elif key in _dict_keys:
                    default = {}
                else:
                    default = []
            self._data[key] = default
        else:
            self._data[key] = result
        self._loaded_keys.add(key)

    @classmethod
    def _progress_source_label(cls, key: str) -> str:
        """Return a compact display label for loading-progress source status."""
        return cls._PROGRESS_SOURCE_LABELS.get(
            key,
            key.replace("_", " ").strip().title(),
        )

    @classmethod
    def _format_active_sources(cls, source_keys: set[str]) -> str:
        """Format currently active source fetches for progress text."""
        if not source_keys:
            return ""
        labels = sorted(
            (cls._progress_source_label(key) for key in source_keys),
            key=str.lower,
        )
        visible = labels[: cls._PROGRESS_ACTIVE_SOURCE_LIMIT]
        if len(labels) > cls._PROGRESS_ACTIVE_SOURCE_LIMIT:
            remaining = len(labels) - cls._PROGRESS_ACTIVE_SOURCE_LIMIT
            return f"{', '.join(visible)} +{remaining} more"
        return ", ".join(visible)

    def _emit_partial_source_update(self, key: str, value: Any) -> None:
        """Store partial source value and trigger an incremental UI refresh."""
        self._data[key] = value
        now = time.monotonic()
        last_emit_at = self._last_partial_emit_at.get(key, 0.0)
        if now - last_emit_at < self._PARTIAL_SOURCE_EMIT_INTERVAL_SECONDS:
            return
        self._last_partial_emit_at[key] = now
        if not bool(getattr(self._screen, "is_current", True)):
            return
        try:
            self._screen.post_message(ClusterSourceLoaded(key))
        except Exception:
            logger.debug("Skipping partial source update for %s", key, exc_info=True)

    async def _load_streaming_pod_request_stats(
        self,
        ctrl: ClusterController,
    ) -> dict[str, Any]:
        """Load pod request stats with namespace-level incremental updates."""

        def _on_namespace_update(
            partial_stats: dict[str, Any],
            _completed: int,
            _total: int,
        ) -> None:
            self._emit_partial_source_update("pod_request_stats", partial_stats)

        return await ctrl.get_pod_request_stats(
            on_namespace_update=_on_namespace_update
        )

    async def _load_streaming_pod_distribution(
        self,
        ctrl: ClusterController,
    ) -> Any:
        """Load pod distribution with namespace-level incremental updates."""

        def _on_namespace_update(
            partial_distribution: Any,
            _completed: int,
            _total: int,
        ) -> None:
            self._emit_partial_source_update("pod_distribution", partial_distribution)

        return await ctrl.fetch_pod_distribution(
            on_namespace_update=_on_namespace_update
        )

    async def _load_streaming_nodes(
        self,
        ctrl: ClusterController,
    ) -> list:
        """Load nodes progressively and render rows as they arrive."""

        def _on_node_update(
            partial_nodes: list,
            completed: int,
            total: int,
        ) -> None:
            now = time.monotonic()
            # Keep node-derived widgets responsive while avoiding O(n) rebuilds
            # on every namespace tick for large clusters.
            should_refresh_derived = (
                total <= 0
                or completed >= total
                or now - self._last_node_derived_emit_at
                >= self._PARTIAL_NODE_DERIVED_EMIT_INTERVAL_SECONDS
            )
            if should_refresh_derived:
                self._last_node_derived_emit_at = now
                self._data.update(self._build_derived_node_sources(partial_nodes))
            self._emit_partial_source_update("nodes", partial_nodes)
        nodes = await ctrl.fetch_nodes(
            include_pod_resources=True,
            on_node_update=_on_node_update,
        )
        await self._cache_derived_node_sources(nodes)
        return nodes

    async def _cache_derived_node_sources(self, nodes: list) -> None:
        """Persist derived node sources once per node fetch completion."""
        derived_sources = await asyncio.to_thread(
            self._build_derived_node_sources,
            nodes,
        )
        self._data.update(derived_sources)

    def _build_derived_node_sources(self, nodes: list) -> dict[str, Any]:
        """Build node-derived sources off the UI thread."""
        return {
            "node_conditions": self._derive_node_conditions(nodes),
            "node_taints": self._derive_node_taints(nodes),
            "az_distribution": self._derive_az_distribution(nodes),
            "instance_type_distribution": self._derive_instance_type_distribution(nodes),
            "kubelet_version_distribution": self._derive_kubelet_version_distribution(nodes),
            "node_groups_az_matrix": self._derive_node_groups_az_matrix(nodes),
            "node_groups": self._derive_node_groups(nodes),
            "high_pod_count_nodes": self._derive_high_pod_count_nodes(nodes),
        }

    @staticmethod
    def _derive_node_conditions(nodes: list) -> dict[str, dict[str, int]]:
        """Derive node condition counts from partial node list."""
        condition_types = [
            "Ready",
            "MemoryPressure",
            "DiskPressure",
            "PIDPressure",
            "NetworkUnavailable",
        ]
        conditions: dict[str, dict[str, int]] = {
            cond: {"True": 0, "False": 0, "Unknown": 0}
            for cond in condition_types
        }
        for node in nodes:
            for cond_type, status in getattr(node, "conditions", {}).items():
                if cond_type in conditions:
                    if status in conditions[cond_type]:
                        conditions[cond_type][status] += 1
                    else:
                        conditions[cond_type]["Unknown"] += 1
        return conditions

    @staticmethod
    def _derive_node_taints(nodes: list) -> dict[str, Any]:
        """Derive taint distribution from partial node list."""
        nodes_with_taints = 0
        taint_distribution: dict[str, dict[str, Any]] = {}
        for node in nodes:
            taints = getattr(node, "taints", [])
            if taints:
                nodes_with_taints += 1
            for taint in taints:
                key = taint.get("key", "")
                effect = taint.get("effect", "Unknown")
                taint_key = f"{key}={taint.get('value', '')}" if key else effect
                if taint_key not in taint_distribution:
                    taint_distribution[taint_key] = {"effect": effect, "count": 0}
                taint_distribution[taint_key]["count"] += 1
        return {
            "total_nodes_with_taints": nodes_with_taints,
            "taint_distribution": taint_distribution,
        }

    @staticmethod
    def _derive_az_distribution(nodes: list) -> dict[str, int]:
        """Derive AZ distribution from partial node list."""
        counts: dict[str, int] = {}
        for node in nodes:
            az = getattr(node, "availability_zone", "")
            if az:
                counts[az] = counts.get(az, 0) + 1
        return counts

    @staticmethod
    def _derive_instance_type_distribution(nodes: list) -> dict[str, int]:
        """Derive instance-type distribution from partial node list."""
        counts: dict[str, int] = {}
        for node in nodes:
            instance_type = getattr(node, "instance_type", "")
            if instance_type:
                counts[instance_type] = counts.get(instance_type, 0) + 1
        return counts

    @staticmethod
    def _derive_kubelet_version_distribution(nodes: list) -> dict[str, int]:
        """Derive kubelet-version distribution from partial node list."""
        counts: dict[str, int] = {}
        for node in nodes:
            version = str(getattr(node, "kubelet_version", "")).lstrip("v")
            if version:
                counts[version] = counts.get(version, 0) + 1
        return counts

    @staticmethod
    def _derive_node_groups_az_matrix(nodes: list) -> dict[str, dict[str, int]]:
        """Derive node-group/AZ matrix from partial node list."""
        matrix: dict[str, dict[str, int]] = {}
        for node in nodes:
            ng = getattr(node, "node_group", "Unknown")
            az = getattr(node, "availability_zone", "Unknown")
            if ng not in matrix:
                matrix[ng] = {}
            matrix[ng][az] = matrix[ng].get(az, 0) + 1
        return matrix

    def _derive_node_groups(self, nodes: list) -> dict[str, dict[str, Any]]:
        """Derive node-group allocation summary from partial node list."""
        node_groups: dict[str, dict[str, Any]] = {}
        for node in nodes:
            ng = getattr(node, "node_group", "Unknown")
            if ng not in node_groups:
                node_groups[ng] = {
                    "cpu_allocatable": 0.0,
                    "memory_allocatable": 0.0,
                    "cpu_requests": 0.0,
                    "memory_requests": 0.0,
                    "cpu_limits": 0.0,
                    "memory_limits": 0.0,
                    "node_count": 0,
                }
            node_groups[ng]["cpu_allocatable"] += self._safe_float(
                getattr(node, "cpu_allocatable", 0.0)
            )
            node_groups[ng]["memory_allocatable"] += self._safe_float(
                getattr(node, "memory_allocatable", 0.0)
            )
            node_groups[ng]["cpu_requests"] += self._safe_float(
                getattr(node, "cpu_requests", 0.0)
            )
            node_groups[ng]["memory_requests"] += self._safe_float(
                getattr(node, "memory_requests", 0.0)
            )
            node_groups[ng]["cpu_limits"] += self._safe_float(
                getattr(node, "cpu_limits", 0.0)
            )
            node_groups[ng]["memory_limits"] += self._safe_float(
                getattr(node, "memory_limits", 0.0)
            )
            node_groups[ng]["node_count"] += 1

        result: dict[str, dict[str, Any]] = {}
        for ng, totals in node_groups.items():
            cpu_pct = (
                (totals["cpu_requests"] / totals["cpu_allocatable"] * 100)
                if totals["cpu_allocatable"] > 0
                else 0.0
            )
            mem_pct = (
                (totals["memory_requests"] / totals["memory_allocatable"] * 100)
                if totals["memory_allocatable"] > 0
                else 0.0
            )
            cpu_lim_pct = (
                (totals["cpu_limits"] / totals["cpu_allocatable"] * 100)
                if totals["cpu_allocatable"] > 0
                else 0.0
            )
            mem_lim_pct = (
                (totals["memory_limits"] / totals["memory_allocatable"] * 100)
                if totals["memory_allocatable"] > 0
                else 0.0
            )
            result[ng] = {
                "cpu_allocatable": totals["cpu_allocatable"],
                "memory_allocatable": totals["memory_allocatable"],
                "cpu_requests": totals["cpu_requests"],
                "memory_requests": totals["memory_requests"],
                "cpu_limits": totals["cpu_limits"],
                "memory_limits": totals["memory_limits"],
                "cpu_pct": cpu_pct,
                "memory_pct": mem_pct,
                "cpu_lim_pct": cpu_lim_pct,
                "memory_lim_pct": mem_lim_pct,
                "node_count": totals["node_count"],
            }
        return result

    def _derive_high_pod_count_nodes(self, nodes: list) -> list[dict[str, Any]]:
        """Derive high pod-count nodes from partial node list."""
        threshold_pct = 80.0
        high_pod_nodes: list[dict[str, Any]] = []
        for node in nodes:
            pod_count = self._safe_float(getattr(node, "pod_count", 0.0))
            pod_capacity = self._safe_float(getattr(node, "pod_capacity", 0.0))
            pod_pct = (pod_count / pod_capacity * 100) if pod_capacity > 0 else 0.0
            if pod_pct >= threshold_pct:
                high_pod_nodes.append(
                    {
                        "name": str(getattr(node, "name", "")),
                        "node_group": str(getattr(node, "node_group", "")),
                        "pod_count": int(pod_count),
                        "max_pods": int(pod_capacity),
                        "pod_pct": pod_pct,
                    }
                )
        high_pod_nodes.sort(key=lambda item: item["pod_pct"], reverse=True)
        return high_pod_nodes

    async def _load_streaming_pdbs(
        self,
        ctrl: ClusterController,
    ) -> list:
        """Load PDBs progressively by namespace."""

        def _on_namespace_update(
            partial_rows: list,
            _completed: int,
            _total: int,
        ) -> None:
            self._emit_partial_source_update("pdbs", partial_rows)

        return await ctrl.fetch_pdbs(on_namespace_update=_on_namespace_update)

    async def _load_streaming_single_replica(
        self,
        ctrl: ClusterController,
    ) -> list:
        """Load single-replica workloads progressively by namespace."""

        def _on_namespace_update(
            partial_rows: list,
            _completed: int,
            _total: int,
        ) -> None:
            self._emit_partial_source_update("single_replica", partial_rows)

        return await ctrl.fetch_single_replica_workloads(
            on_namespace_update=_on_namespace_update
        )

    async def _load_streaming_all_workloads(
        self,
        ctrl: ClusterController,
    ) -> list:
        """Load runtime workload inventory progressively by namespace."""

        def _on_namespace_update(
            partial_rows: list,
            _completed: int,
            _total: int,
        ) -> None:
            self._emit_partial_source_update("all_workloads", partial_rows)

        return await ctrl.fetch_workload_inventory(
            on_namespace_update=_on_namespace_update
        )

    @staticmethod
    def _default_charts_overview() -> dict[str, Any]:
        """Fallback charts KPI payload when local chart analysis is unavailable."""
        return {
            "available": False,
            "total_charts": 0,
            "team_count": 0,
            "single_replica_charts": 0,
            "charts_with_pdb_template": 0,
            "charts_with_pdb": 0,
            "pdb_coverage_pct": 0.0,
        }

    async def _load_charts_overview(self) -> dict[str, Any]:
        """Load chart-level KPI summary from configured local charts path."""
        app = getattr(self._screen, "app", None)
        settings = getattr(app, "settings", None)
        charts_path_raw = str(getattr(settings, "charts_path", "") or "").strip()
        normalize_optional_path = getattr(app, "_normalize_optional_path", None)
        if callable(normalize_optional_path):
            charts_path_raw = str(normalize_optional_path(charts_path_raw)).strip()
        if not charts_path_raw:
            return self._default_charts_overview()

        charts_path = Path(charts_path_raw).expanduser().resolve()
        if not charts_path.is_dir():
            return self._default_charts_overview()

        codeowners_path: Path | None = None
        codeowners_raw = str(getattr(settings, "codeowners_path", "") or "").strip()
        if callable(normalize_optional_path):
            codeowners_raw = str(normalize_optional_path(codeowners_raw)).strip()
        if codeowners_raw:
            candidate = Path(codeowners_raw).expanduser().resolve()
            if candidate.is_file():
                codeowners_path = candidate
        if codeowners_path is None:
            default_codeowners = charts_path / "CODEOWNERS"
            if default_codeowners.exists():
                codeowners_path = default_codeowners

        from kubeagle.controllers import ChartsController

        charts_controller = ChartsController(
            charts_path,
            codeowners_path=codeowners_path,
        )
        charts = await charts_controller.analyze_all_charts_async()
        total_charts = len(charts)
        team_count = len({chart.team for chart in charts if chart.team})
        single_replica = sum(1 for chart in charts if chart.replicas == 1)
        charts_with_template = sum(1 for chart in charts if chart.pdb_template_exists)
        charts_with_pdb = sum(1 for chart in charts if chart.pdb_enabled)
        coverage_pct = (
            (charts_with_pdb / total_charts) * 100.0
            if total_charts > 0
            else 0.0
        )
        return {
            "available": True,
            "total_charts": total_charts,
            "team_count": team_count,
            "single_replica_charts": single_replica,
            "charts_with_pdb_template": charts_with_template,
            "charts_with_pdb": charts_with_pdb,
            "pdb_coverage_pct": coverage_pct,
        }

    async def _load_existing_source_value(self, key: str, default: Any) -> Any:
        """Resolve a source from already streamed in-memory data."""
        return self._data.get(key, default)

    async def _load_streaming_event_summary(
        self,
        ctrl: ClusterController,
    ) -> EventSummary:
        """Load event summary with namespace-level incremental updates."""

        def _on_namespace_update(
            partial_summary: EventSummary,
            _completed: int,
            _total: int,
        ) -> None:
            self._emit_partial_source_update("event_summary", partial_summary)

        return await ctrl.get_event_summary(
            max_age_hours=self._event_window_hours,
            on_namespace_update=_on_namespace_update,
        )

    async def _load_streaming_events(
        self,
        ctrl: ClusterController,
    ) -> dict[str, int]:
        """Load event counters with namespace-level incremental updates."""

        def _on_namespace_update(
            partial_counts: dict[str, int],
            _completed: int,
            _total: int,
        ) -> None:
            self._emit_partial_source_update("events", partial_counts)

        return await ctrl.fetch_events(
            max_age_hours=self._event_window_hours,
            on_namespace_update=_on_namespace_update,
        )

    async def _load_streaming_critical_events(
        self,
        ctrl: ClusterController,
    ) -> list[EventDetail]:
        """Load critical event rows with namespace-level incremental updates."""

        def _on_namespace_update(
            partial_critical_events: list[EventDetail],
            _completed: int,
            _total: int,
        ) -> None:
            self._emit_partial_source_update(
                "critical_events",
                partial_critical_events,
            )

        return await ctrl.get_critical_events(
            max_age_hours=self._event_window_hours,
            on_namespace_update=_on_namespace_update,
        )

    def _build_source_specs(self, ctrl: ClusterController) -> tuple[_SourceSpec, ...]:
        """Build source loaders in tab-balanced order for parallel execution."""
        return (
            # Start one primary source per major tab early, so tab payloads
            # stream in parallel even with a constrained semaphore.
            _SourceSpec("nodes", lambda: self._load_streaming_nodes(ctrl), []),
            _SourceSpec("all_workloads", lambda: self._load_streaming_all_workloads(ctrl), []),
            _SourceSpec("events", lambda: self._load_streaming_events(ctrl), []),
            _SourceSpec("pdbs", lambda: self._load_streaming_pdbs(ctrl), []),
            _SourceSpec("event_summary", lambda: self._load_streaming_event_summary(ctrl), None),
            _SourceSpec(
                "charts_overview",
                self._load_charts_overview,
                self._default_charts_overview(),
            ),
            _SourceSpec("critical_events", lambda: self._load_streaming_critical_events(ctrl), []),
            _SourceSpec(
                "pod_distribution",
                lambda: self._load_streaming_pod_distribution(ctrl),
                None,
            ),
            _SourceSpec(
                "single_replica",
                lambda: self._load_streaming_single_replica(ctrl),
                [],
            ),
            _SourceSpec(
                "pod_request_stats",
                lambda: self._load_streaming_pod_request_stats(ctrl),
                {},
            ),
            _SourceSpec(
                "node_groups",
                lambda: self._load_existing_source_value("node_groups", {}),
                {},
            ),
            _SourceSpec(
                "node_groups_az_matrix",
                lambda: self._load_existing_source_value("node_groups_az_matrix", {}),
                {},
            ),
            _SourceSpec(
                "node_conditions",
                lambda: self._load_existing_source_value("node_conditions", {}),
                {},
            ),
            _SourceSpec(
                "node_taints",
                lambda: self._load_existing_source_value("node_taints", {}),
                {},
            ),
            _SourceSpec(
                "az_distribution",
                lambda: self._load_existing_source_value("az_distribution", {}),
                {},
            ),
            _SourceSpec(
                "instance_type_distribution",
                lambda: self._load_existing_source_value(
                    "instance_type_distribution",
                    {},
                ),
                {},
            ),
            _SourceSpec(
                "kubelet_version_distribution",
                lambda: self._load_existing_source_value(
                    "kubelet_version_distribution",
                    {},
                ),
                {},
            ),
            _SourceSpec(
                "high_pod_count_nodes",
                lambda: self._load_existing_source_value("high_pod_count_nodes", []),
                [],
            ),
        )

    def _reset_source_defaults(self, source_specs: tuple[_SourceSpec, ...]) -> None:
        """Clear source slots to avoid stale data bleed-through between refreshes."""
        for spec in source_specs:
            self._data[spec.key] = spec.default

    async def _load_cluster_data_worker(self) -> None:
        """Load cluster sources in parallel with progressive per-source updates."""
        worker = get_current_worker()
        force_refresh = self._force_refresh_next_load
        self._force_refresh_next_load = False

        def msg(text: str) -> None:
            if not bool(getattr(self._screen, "is_current", True)):
                return
            self._screen.call_later(self._screen._update_loading_message, text)

        def cancelled() -> bool:
            return worker.is_cancelled

        pending_tasks: set[asyncio.Task[None]] = set()

        try:
            self._partial_errors.clear()
            self._loaded_keys.clear()
            self._last_partial_emit_at.clear()
            self._last_node_derived_emit_at = 0.0

            app = self._screen.app
            configured_context = (
                getattr(self._screen, "context", None)
                or getattr(app, "context", None)
            )
            current_context = await asyncio.to_thread(
                ClusterController.resolve_current_context
            )
            # Always prefer active kube context from local kubeconfig.
            context = current_context or configured_context

            msg("Connecting to cluster...")
            if force_refresh:
                ClusterController.clear_global_command_cache(context=context)
            ctrl = ClusterController(context=context)
            # Regression guard: explicit default event window contract.
            # ctrl.fetch_events(max_age_hours=self._DEFAULT_EVENT_WINDOW_HOURS)
            # ctrl.get_event_summary(max_age_hours=self._DEFAULT_EVENT_WINDOW_HOURS)
            # ctrl.get_critical_events(max_age_hours=self._DEFAULT_EVENT_WINDOW_HOURS)
            source_specs = self._build_source_specs(ctrl)
            self._reset_source_defaults(source_specs)

            self._data["cluster_name"] = context if context else "EKS Cluster"

            if cancelled():
                self._is_loading = False
                return

            msg("Checking cluster connection...")
            connection_error_detail = ""
            is_connected = False
            for attempt in range(1, self._CONNECTION_CHECK_ATTEMPTS + 1):
                if attempt > 1:
                    msg(
                        "Re-checking cluster connection "
                        f"({attempt}/{self._CONNECTION_CHECK_ATTEMPTS})..."
                    )
                try:
                    is_connected = await asyncio.wait_for(
                        ctrl.check_cluster_connection(),
                        timeout=self._CONNECTION_CHECK_TIMEOUT_SECONDS,
                    )
                except asyncio.TimeoutError:
                    is_connected = False
                    logger.warning(
                        "Cluster connection check timed out on attempt %s after %.1fs",
                        attempt,
                        self._CONNECTION_CHECK_TIMEOUT_SECONDS,
                    )

                connection_state = ctrl.get_fetch_state(
                    ClusterController.SOURCE_CLUSTER_CONNECTION
                )
                if (
                    connection_state is not None
                    and connection_state.error_message
                ):
                    connection_error_detail = connection_state.error_message

                if is_connected:
                    break
                if attempt < self._CONNECTION_CHECK_ATTEMPTS:
                    await asyncio.sleep(
                        self._CONNECTION_CHECK_RETRY_DELAY_SECONDS * attempt
                    )

            if not is_connected:
                if connection_error_detail:
                    msg(
                        "Connection check unstable "
                        f"({connection_error_detail}); trying direct data fetch..."
                    )
                else:
                    msg("Connection check unstable; trying direct data fetch...")

            semaphore = asyncio.Semaphore(self._MAX_PARALLEL_SOURCES)
            total = len(source_specs)
            completed = 0
            active_sources: set[str] = set()

            def emit_load_status() -> None:
                """Emit progress text with currently active source labels."""
                base = f"Loading data ({completed}/{total})..."
                active_text = self._format_active_sources(active_sources)
                if active_text:
                    msg(f"{base} Fetching: {active_text}")
                    return
                msg(base)

            emit_load_status()

            async def _fetch_source(spec: _SourceSpec) -> None:
                async with semaphore:
                    active_sources.add(spec.key)
                    emit_load_status()
                    try:
                        result = await spec.loader()
                        self._store_result(spec.key, result, default=spec.default)
                    except Exception as exc:
                        self._store_result(spec.key, exc, default=spec.default)
                    finally:
                        active_sources.discard(spec.key)
                if not cancelled() and bool(getattr(self._screen, "is_current", True)):
                    self._screen.post_message(ClusterSourceLoaded(spec.key))

            source_tasks = [asyncio.create_task(_fetch_source(spec)) for spec in source_specs]
            pending_tasks.update(source_tasks)
            try:
                for future in asyncio.as_completed(source_tasks):
                    await future
                    completed += 1
                    if cancelled():
                        return
                    emit_load_status()
            finally:
                for task in source_tasks:
                    pending_tasks.discard(task)

            # Post final message
            if len(self._partial_errors) == total:
                message = "All data sources failed to load"
                if connection_error_detail:
                    message = (
                        f"{message}. Connection check: {connection_error_detail}"
                    )
                self._screen.post_message(
                    ClusterDataLoadFailed(message)
                )
            else:
                self._screen.post_message(ClusterDataLoaded())

        except asyncio.CancelledError:
            # Refresh actions intentionally cancel in-flight workers.
            return
        except Exception as e:
            logger.exception("Failed to load cluster data")
            self._screen.post_message(ClusterDataLoadFailed(self._friendly_error(e)))
        finally:
            for task in list(pending_tasks):
                if task.done():
                    continue
                task.cancel()
            if pending_tasks:
                await asyncio.gather(*pending_tasks, return_exceptions=True)
            self._is_loading = False

    # =========================================================================
    # Counting / Aggregation
    # =========================================================================

    def count_ready_nodes(self) -> tuple[int, int]:
        """Returns (ready_count, total_count)."""
        node_summary = summarize_nodes(self.get_nodes())
        return node_summary["ready_count"], node_summary["node_count"]

    def count_events_by_type(self) -> dict[str, int]:
        events = self.get_events()
        if isinstance(events, dict):
            if "Warning" in events or "Error" in events:
                return events
            summary = self.get_event_summary()
            if summary is not None:
                warning_total = (
                    summary.oom_count
                    + summary.node_not_ready_count
                    + summary.failed_scheduling_count
                    + summary.backoff_count
                    + summary.unhealthy_count
                    + summary.failed_mount_count
                    + summary.evicted_count
                )
                error_total = (
                    summary.oom_count
                    + summary.node_not_ready_count
                    + summary.failed_scheduling_count
                    + summary.evicted_count
                )
                return {
                    "Warning": warning_total,
                    "Error": error_total,
                }
            return events
        counts: dict[str, int] = {}
        for event in events:
            t = event.type.value if hasattr(event.type, "value") else str(event.type)
            counts[t] = counts.get(t, 0) + 1
        return counts

    def count_warning_events(self) -> int:
        summary = self.get_event_summary()
        if summary is not None:
            return (
                summary.oom_count
                + summary.node_not_ready_count
                + summary.failed_scheduling_count
                + summary.backoff_count
                + summary.unhealthy_count
                + summary.failed_mount_count
                + summary.evicted_count
            )
        events = self.get_events()
        if isinstance(events, dict):
            return events.get("Warning", 0)
        return sum(1 for e in events if e.type.value == "Warning")

    def count_error_events(self) -> int:
        summary = self.get_event_summary()
        if summary is not None:
            return (
                summary.oom_count
                + summary.node_not_ready_count
                + summary.failed_scheduling_count
                + summary.evicted_count
            )
        events = self.get_events()
        if isinstance(events, dict):
            return events.get("Error", 0)
        return sum(1 for e in events if e.type.value == "Error")

    def count_blocking_pdbs(self) -> int:
        return count_blocking_pdbs(self.get_pdbs())

    def _calc_health(self) -> tuple[str, int, list[str]]:
        """Core health calculation. Returns (status_str, score, issues)."""
        ready, total = self.count_ready_nodes()
        errors = self.count_error_events()
        warnings = self.count_warning_events()
        blocking = self.count_blocking_pdbs()

        score = 100
        issues: list[str] = []

        if total > 0:
            pct = (ready / total) * 100
            score *= pct / 100
            if pct < 90:
                issues.append(f"Only {ready}/{total} nodes ready")
        else:
            score = 0
            issues.append("No nodes found")

        score -= min(
            errors * self._ERROR_PENALTY_PER_EVENT,
            self._ERROR_PENALTY_CAP,
        )
        if errors > 0:
            issues.append(f"{errors} error events")
        score -= min(
            warnings * self._WARNING_PENALTY_PER_EVENT,
            self._WARNING_PENALTY_CAP,
        )
        if warnings > 5:
            issues.append(f"{warnings} warning events")
        score -= min(
            blocking * self._BLOCKING_PENALTY_PER_EVENT,
            self._BLOCKING_PENALTY_CAP,
        )
        if blocking > 0:
            issues.append(f"{blocking} blocking PDBs")

        score = max(0, min(100, score))
        if score >= 90:
            label = "[#30d158]HEALTHY[/#30d158]"
        elif score >= 70:
            label = "[#ff9f0a]DEGRADED[/#ff9f0a]"
        else:
            label = "[bold #ff3b30]UNHEALTHY[/bold #ff3b30]"

        return label, int(score), issues

    def get_health_status(self) -> tuple[str, list[str]]:
        """Returns (status_str, issues_list)."""
        label, _score, issues = self._calc_health()
        return label, issues

    def get_health_data(self) -> tuple[str, int, list[str]]:
        """Returns (status_str, score, issues_list)."""
        return self._calc_health()

    def get_sorted_events(self, limit: int = MAX_EVENTS_DISPLAY) -> list:
        """Get events sorted by time (newest first)."""
        events = self.get_events()
        if isinstance(events, dict):
            return []
        return sorted(events, key=lambda e: e.last_timestamp or datetime.min, reverse=True)[:limit]

    # =========================================================================
    # Row Formatting (return data for table widgets)
    # =========================================================================

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        """Safely convert a value to float (handles MagicMock in tests)."""
        try:
            return float(value) if value is not None else default
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _truncate_text(value: Any, max_length: int) -> str:
        """Truncate long values to fit fixed-width table columns."""
        text = str(value or "")
        if len(text) <= max_length:
            return text
        if max_length <= 3:
            return text[:max_length]
        return f"{text[:max_length - 3]}..."

    def get_node_rows(self) -> list[tuple]:
        rows: list[tuple] = []

        def _format_cpu_m(value: float) -> str:
            return f"{value:.0f}m"

        def _format_mem_gib(value: float) -> str:
            return f"{value / 1024 / 1024 / 1024:.2f}Gi"

        def _format_alloc_pair(
            used: float,
            alloc: float,
            *,
            value_formatter: Callable[[float], str],
        ) -> str:
            used_text = value_formatter(used)
            if alloc <= 0:
                return f"- ({used_text}/-)"
            alloc_text = value_formatter(alloc)
            used_pct = (used / alloc) * 100
            return f"{self._format_alloc_pct(used_pct)} ({used_text}/{alloc_text})"

        for node in self.get_nodes():
            cpu_alloc = self._safe_float(getattr(node, "cpu_allocatable", 0))
            mem_alloc = self._safe_float(getattr(node, "memory_allocatable", 0))
            cpu_req = self._safe_float(node.cpu_requests)
            mem_req = self._safe_float(node.memory_requests)
            cpu_lim = self._safe_float(getattr(node, "cpu_limits", 0))
            mem_lim = self._safe_float(getattr(node, "memory_limits", 0))
            pod_count = int(self._safe_float(getattr(node, "pod_count", 0)))
            max_pods_raw = getattr(node, "pod_capacity", None)
            if max_pods_raw in (None, 0):
                max_pods_raw = getattr(node, "max_pods", 0)
            max_pods = int(self._safe_float(max_pods_raw))
            if max_pods > 0:
                pod_usage_pct = (pod_count / max_pods) * 100
                pod_usage_display = (
                    f"{self._format_alloc_pct(pod_usage_pct)} ({pod_count}/{max_pods})"
                )
            else:
                pod_usage_display = f"- ({pod_count}/-)"
            cpu_req_display = _format_alloc_pair(
                cpu_req,
                cpu_alloc,
                value_formatter=_format_cpu_m,
            )
            mem_req_display = _format_alloc_pair(
                mem_req,
                mem_alloc,
                value_formatter=_format_mem_gib,
            )
            cpu_lim_display = _format_alloc_pair(
                cpu_lim,
                cpu_alloc,
                value_formatter=_format_cpu_m,
            )
            mem_lim_display = _format_alloc_pair(
                mem_lim,
                mem_alloc,
                value_formatter=_format_mem_gib,
            )
            ng = getattr(node, "node_group", "Unknown")
            ng_str = str(ng) if ng else "Unknown"
            node_name = self._truncate_text(node.name, self._NODE_NAME_MAX_LENGTH)
            rows.append((
                node_name,
                ng_str,
                pod_usage_display,
                cpu_req_display,
                mem_req_display,
                cpu_lim_display,
                mem_lim_display,
            ))
        return rows

    def get_pod_dist_stats_rows(self) -> list[tuple]:
        """Pod count statistics per node (min/avg/max/p95)."""
        dist = self.get_pod_distribution()
        if not dist:
            return []
        return [
            ("Total Pods", str(dist.total_pods)),
            ("Min per Node", str(dist.min_pods_per_node)),
            ("Avg per Node", f"{dist.avg_pods_per_node:.1f}"),
            ("Max per Node", str(dist.max_pods_per_node)),
            ("P95 per Node", f"{dist.p95_pods_per_node:.1f}"),
        ]

    def get_event_summary_rows(self) -> list[tuple]:
        """Event category summary rows."""
        rows: list[tuple] = []
        summary = self.get_event_summary()
        if summary is not None:
            categories = [
                ("OOMKilling", summary.oom_count),
                ("NodeNotReady", summary.node_not_ready_count),
                ("FailedScheduling", summary.failed_scheduling_count),
                ("BackOff", summary.backoff_count),
                ("Unhealthy", summary.unhealthy_count),
                ("FailedMount", summary.failed_mount_count),
                ("Evicted", summary.evicted_count),
            ]
            for name, count in categories:
                indicator = (
                    "[#30d158]OK[/#30d158]"
                    if count == 0
                    else "[bold #ff9f0a]Alert[/bold #ff9f0a]"
                )
                color = "green" if count == 0 else "#ff3b30"
                rows.append((f"[{color}]{name}[/{color}]", str(count), indicator))
        else:
            # Fallback to raw event type counts
            events = self.get_events()
            if isinstance(events, dict):
                for etype, count in sorted(events.items(), key=lambda x: x[1], reverse=True):
                    if count == 0:
                        indicator = "[#30d158]OK[/#30d158]"
                    elif etype == "Warning":
                        indicator = "[bold #ff9f0a]Alert[/bold #ff9f0a]"
                    else:
                        indicator = "[bold #ff3b30]Alert[/bold #ff3b30]"
                    color = "#ff3b30" if etype == "Warning" else "yellow"
                    rows.append((f"[{color}]{etype}[/{color}]", str(count), indicator))
        return rows

    def get_event_detail_rows(self) -> list[tuple]:
        """Detailed critical event rows."""
        rows: list[tuple] = []
        for ev in self.get_critical_events():
            if ev.type == "Warning":
                type_color = "#ff3b30"
                type_value = f"{ev.type}"
            else:
                type_color = "#ff9f0a"
                type_value = f"{ev.type}"
            rows.append((
                f"[{type_color}]{type_value}[/{type_color}]",
                ev.reason,
                ev.involved_object,
                str(ev.count),
                ev.message,
            ))
        return rows

    def get_pdb_rows(self) -> list[tuple]:
        rows: list[tuple] = []
        for p in self.get_pdbs():
            st = (
                "[#30d158]Healthy[/#30d158]"
                if not p.is_blocking
                else "[bold #ff3b30]Blocking[/bold #ff3b30]"
            )
            expected_pods = str(getattr(p, "expected_pods", "N/A"))
            current_healthy = str(getattr(p, "current_healthy", "N/A"))
            disruptions = str(getattr(p, "disruptions_allowed", "N/A"))
            unhealthy_policy = str(getattr(p, "unhealthy_pod_eviction_policy", "N/A"))
            blocking_reason = getattr(p, "blocking_reason", None)
            issues = str(blocking_reason) if blocking_reason else ""
            if not issues and p.is_blocking:
                issues = "[#ff9f0a]Budget may block disruptions[/#ff9f0a]"
            rows.append((
                p.namespace,
                p.name,
                str(p.min_available) if p.min_available is not None else "N/A",
                str(p.max_unavailable) if p.max_unavailable is not None else "N/A",
                expected_pods,
                current_healthy,
                disruptions,
                unhealthy_policy,
                st,
                issues if issues else "-",
            ))
        return rows

    def get_pdb_coverage_summary_rows(self) -> list[tuple]:
        """Chart-level PDB coverage summary rows."""
        charts_overview = self.get_charts_overview()
        total = int(charts_overview.get("total_charts", 0))
        with_template = int(charts_overview.get("charts_with_pdb_template", 0))
        with_enabled = int(charts_overview.get("charts_with_pdb", 0))
        coverage_pct = (with_enabled / total * 100) if total > 0 else 0.0
        template_pct = (with_template / total * 100) if total > 0 else 0.0
        coverage_color = "green" if coverage_pct >= 50 else "#ff3b30"
        template_color = "green" if template_pct >= 50 else "yellow"
        return [
            ("Total Charts", str(total)),
            ("Charts with PDB Template", str(with_template)),
            ("Charts with PDB Enabled", str(with_enabled)),
            ("PDB Coverage", f"[{coverage_color}]{coverage_pct:.1f}%[/{coverage_color}]"),
            ("Template Coverage", f"[{template_color}]{template_pct:.1f}%[/{template_color}]"),
        ]

    def get_runtime_pdb_coverage_summary_rows(self) -> list[tuple]:
        """Runtime workload PDB coverage summary rows."""
        workloads = self.get_all_workloads()
        total = len(workloads)
        with_pdb = sum(1 for workload in workloads if bool(getattr(workload, "has_pdb", False)))
        coverage_pct = (with_pdb / total * 100) if total > 0 else 0.0
        coverage_color = "green" if coverage_pct >= 50 else "#ff3b30"
        return [
            ("Total Runtime Workloads", str(total)),
            ("Runtime Workloads with PDB", str(with_pdb)),
            ("Runtime PDB Coverage", f"[{coverage_color}]{coverage_pct:.1f}%[/{coverage_color}]"),
        ]

    def get_all_workload_rows(self) -> list[tuple]:
        """Runtime workload inventory rows for Workloads tab."""
        rows: list[tuple] = []
        for workload in self.get_all_workloads():
            desired_raw = getattr(workload, "desired_replicas", None)
            ready_raw = getattr(workload, "ready_replicas", None)
            desired = str(desired_raw) if desired_raw is not None else "-"
            ready = str(ready_raw) if ready_raw is not None else "-"
            helm_release = str(getattr(workload, "helm_release", "") or "-")
            has_pdb = bool(getattr(workload, "has_pdb", False))
            pdb_state = (
                "[#30d158]✅ Yes[/#30d158]"
                if has_pdb
                else "[bold #ff9f0a]No[/bold #ff9f0a]"
            )

            status_text = str(getattr(workload, "status", "Unknown") or "Unknown")
            lowered_status = status_text.lower()
            if lowered_status in {"ready", "running", "succeeded", "idle"}:
                status_display = f"[#30d158]{status_text}[/#30d158]"
            elif lowered_status in {"progressing", "pending", "scaledtozero", "suspended"}:
                status_display = f"[#ff9f0a]{status_text}[/#ff9f0a]"
            elif lowered_status in {"notready", "failed"}:
                status_display = f"[bold #ff3b30]{status_text}[/bold #ff3b30]"
            else:
                status_display = status_text

            rows.append((
                str(getattr(workload, "namespace", "")),
                str(getattr(workload, "kind", "")),
                str(getattr(workload, "name", "")),
                desired,
                ready,
                helm_release,
                pdb_state,
                status_display,
            ))
        return rows

    def get_single_replica_rows(self) -> list[tuple]:
        rows: list[tuple] = []
        for wl in self.get_single_replica():
            s = str(wl.status)
            st = f"[#ff9f0a]{s}[/#ff9f0a]" if s == "Ready" else f"[bold #ff3b30]{s}[/bold #ff3b30]"
            replicas = str(getattr(wl, "replicas", 1))
            ready_count = getattr(wl, "ready_replicas", 0)
            ready_str = f"{ready_count}/{replicas}"
            # C3: Add status indicators to Ready column
            if ready_count and str(ready_count) == replicas:
                ready_display = f"[#30d158]{ready_str}[/#30d158]"
            else:
                ready_display = f"[bold #ff3b30]{ready_str}[/bold #ff3b30]"
            helm = str(wl.helm_release) if wl.helm_release else "-"
            rows.append((wl.namespace, wl.name, wl.kind, replicas, ready_display, helm, st))
        return rows

    def _format_pct(self, value: float) -> str:
        """Format percentage with color coding."""
        text = f"{value:.0f}%"
        if value > 90:
            return f"[bold #ff3b30]{text}[/bold #ff3b30]"
        if value > 70:
            return f"[bold #ff9f0a]{text}[/bold #ff9f0a]"
        if value > 0:
            return f"[#30d158]{text}[/#30d158]"
        return text

    def _format_alloc_pct(self, value: float) -> str:
        """Format allocation percentage with overcommit warning."""
        text = f"{value:.0f}%"
        if value > 100:
            return f"[bold #ff3b30]{text}[/bold #ff3b30]"
        if value > 90:
            return f"[bold #ff9f0a]{text}[/bold #ff9f0a]"
        if value > 70:
            return f"[#ff9f0a]{text}[/#ff9f0a]"
        if value > 0:
            return f"[#30d158]{text}[/#30d158]"
        return text

    def get_node_dist_rows(self) -> list[tuple]:
        rows: list[tuple] = []
        # Availability Zone distribution
        for az, count in sorted(self.get_az_distribution().items()):
            rows.append(("Availability Zone", az, str(count)))
        # Instance Type distribution
        for itype, count in sorted(self.get_instance_type_distribution().items(), key=lambda x: x[1], reverse=True):
            rows.append(("Instance Type", itype, str(count)))
        # Kubelet Version distribution
        for version, count in sorted(self.get_kubelet_version_distribution().items()):
            rows.append(("Kubelet Version", f"v{version}" if not version.startswith("v") else version, str(count)))
        # Node Groups by AZ matrix
        for ng, az_counts in sorted(self.get_node_groups_az_matrix().items()):
            for az, count in sorted(az_counts.items()):
                rows.append((f"Group: {ng}", az, str(count)))
        return rows

    def _percentile(self, values: list[float], pct: float) -> float:
        """Compute a percentile from a sorted list of floats."""
        if not values:
            return 0.0
        s = sorted(values)
        idx = pct / 100.0 * (len(s) - 1)
        lo = int(idx)
        hi = min(lo + 1, len(s) - 1)
        frac = idx - lo
        return s[lo] + (s[hi] - s[lo]) * frac

    @classmethod
    def _group_az_columns(
        cls,
        az_names: set[str],
    ) -> tuple[tuple[str, tuple[str, ...]], ...]:
        """Group AZ names by region base (e.g. us-east-1a/b -> us-east-1)."""
        grouped: dict[str, set[str]] = {}
        passthrough: set[str] = set()
        for az_name in az_names:
            match = cls._AWS_AZ_SPLIT_RE.match(az_name.strip().lower())
            if not match:
                passthrough.add(az_name)
                continue
            region, suffix = match.groups()
            grouped.setdefault(region, set()).add(suffix)

        grouped_specs: list[tuple[str, tuple[str, ...]]] = []
        for region in sorted(grouped):
            grouped_specs.append((region, tuple(sorted(grouped[region]))))
        for az_name in sorted(passthrough):
            grouped_specs.append((az_name, ()))
        return tuple(grouped_specs)

    def get_node_group_columns(self) -> list[tuple[str, int]]:
        """Node groups table columns with optional merged AZ matrix columns."""
        matrix = self.get_node_groups_az_matrix()
        all_azs: set[str] = set()
        for az_counts in matrix.values():
            all_azs.update(az_counts.keys())
        grouped_az_specs = self._group_az_columns(all_azs)
        columns = list(NODE_GROUPS_TABLE_COLUMNS)
        for region, suffixes in grouped_az_specs:
            column_name = f"{region} ({'/'.join(suffixes)})" if suffixes else region
            columns.append((column_name, max(12, len(column_name) + 2)))
        return columns

    def get_node_group_rows(self) -> list[tuple]:
        """Node group rows with combined Avg/Max/P95 metric triplets."""
        rows: list[tuple] = []
        node_groups = self.get_node_groups()
        matrix = self.get_node_groups_az_matrix()
        all_azs: set[str] = set()
        for az_counts in matrix.values():
            all_azs.update(az_counts.keys())
        grouped_az_specs = self._group_az_columns(all_azs)
        # Build per-group per-node stats from node data
        group_node_stats: dict[str, list[dict[str, float]]] = {}
        for node in self.get_nodes():
            ng = str(getattr(node, "node_group", "Unknown") or "Unknown")
            cpu_alloc = self._safe_float(getattr(node, "cpu_allocatable", 0))
            mem_alloc = self._safe_float(getattr(node, "memory_allocatable", 0))
            cpu_req = self._safe_float(node.cpu_requests)
            mem_req = self._safe_float(node.memory_requests)
            cpu_lim = self._safe_float(getattr(node, "cpu_limits", 0))
            mem_lim = self._safe_float(getattr(node, "memory_limits", 0))
            cpu_req_pct = (cpu_req / cpu_alloc * 100) if cpu_alloc > 0 else 0
            mem_req_pct = (mem_req / mem_alloc * 100) if mem_alloc > 0 else 0
            cpu_lim_pct = (cpu_lim / cpu_alloc * 100) if cpu_alloc > 0 else 0
            mem_lim_pct = (mem_lim / mem_alloc * 100) if mem_alloc > 0 else 0
            group_node_stats.setdefault(ng, []).append(
                {
                    "cpu_req": cpu_req_pct,
                    "mem_req": mem_req_pct,
                    "cpu_lim": cpu_lim_pct,
                    "mem_lim": mem_lim_pct,
                }
            )

        group_names = sorted(set(node_groups.keys()) | set(group_node_stats.keys()) | set(matrix.keys()))
        for name in group_names:
            data = node_groups.get(name, {})
            if not isinstance(data, dict):
                data = {}
            node_count = int(data.get("node_count", 0) or 0)
            stats = group_node_stats.get(name, [])
            if stats:
                cpu_req_vals = [s["cpu_req"] for s in stats]
                mem_req_vals = [s["mem_req"] for s in stats]
                cpu_lim_vals = [s["cpu_lim"] for s in stats]
                mem_lim_vals = [s["mem_lim"] for s in stats]
                avg_cpu_req = sum(cpu_req_vals) / len(cpu_req_vals)
                max_cpu_req = max(cpu_req_vals)
                p95_cpu_req = self._percentile(cpu_req_vals, 95)
                avg_mem_req = sum(mem_req_vals) / len(mem_req_vals)
                max_mem_req = max(mem_req_vals)
                p95_mem_req = self._percentile(mem_req_vals, 95)
                avg_cpu_lim = sum(cpu_lim_vals) / len(cpu_lim_vals)
                max_cpu_lim = max(cpu_lim_vals)
                p95_cpu_lim = self._percentile(cpu_lim_vals, 95)
                avg_mem_lim = sum(mem_lim_vals) / len(mem_lim_vals)
                max_mem_lim = max(mem_lim_vals)
                p95_mem_lim = self._percentile(mem_lim_vals, 95)
            else:
                # Fallback to group-level aggregates
                cpu_alloc = data.get("cpu_allocatable", 0)
                mem_alloc = data.get("memory_allocatable", 0)
                cpu_req = data.get("cpu_requests", 0)
                mem_req = data.get("memory_requests", 0)
                cpu_lim = data.get("cpu_limits", 0)
                mem_lim = data.get("memory_limits", 0)
                avg_cpu_req = max_cpu_req = p95_cpu_req = (
                    (cpu_req / cpu_alloc * 100) if cpu_alloc > 0 else 0
                )
                avg_mem_req = max_mem_req = p95_mem_req = (
                    (mem_req / mem_alloc * 100) if mem_alloc > 0 else 0
                )
                avg_cpu_lim = max_cpu_lim = p95_cpu_lim = (
                    (cpu_lim / cpu_alloc * 100) if cpu_alloc > 0 else 0
                )
                avg_mem_lim = max_mem_lim = p95_mem_lim = (
                    (mem_lim / mem_alloc * 100) if mem_alloc > 0 else 0
                )

            if node_count <= 0:
                if stats:
                    node_count = len(stats)
                elif name in matrix:
                    node_count = sum(int(matrix[name].get(az, 0)) for az in matrix[name])

            row: list[str] = [
                name,
                str(node_count),
                "/".join((
                    self._format_pct(avg_cpu_req),
                    self._format_pct(max_cpu_req),
                    self._format_pct(p95_cpu_req),
                )),
                "/".join((
                    self._format_pct(avg_mem_req),
                    self._format_pct(max_mem_req),
                    self._format_pct(p95_mem_req),
                )),
                "/".join((
                    self._format_alloc_pct(avg_cpu_lim),
                    self._format_alloc_pct(max_cpu_lim),
                    self._format_alloc_pct(p95_cpu_lim),
                )),
                "/".join((
                    self._format_alloc_pct(avg_mem_lim),
                    self._format_alloc_pct(max_mem_lim),
                    self._format_alloc_pct(p95_mem_lim),
                )),
            ]
            if grouped_az_specs:
                az_counts = matrix.get(name, {})
                for region, suffixes in grouped_az_specs:
                    if suffixes:
                        values = [
                            str(int(az_counts.get(f"{region}{suffix}", 0)))
                            for suffix in suffixes
                        ]
                        row.append("/".join(values))
                    else:
                        row.append(str(int(az_counts.get(region, 0))))
            rows.append(tuple(row))
        return rows

    def get_overview_pod_stats_rows(self) -> list[tuple]:
        """Pod Request Statistics rows for the overview DataTable."""
        stats = self.get_pod_request_stats()
        cpu_req = stats.get("cpu_request_stats", stats.get("cpu_stats", {}))
        cpu_lim = stats.get("cpu_limit_stats", {})
        mem_req = stats.get("memory_request_stats", stats.get("memory_stats", {}))
        mem_lim = stats.get("memory_limit_stats", {})
        rows: list[tuple] = []

        if cpu_req:
            rows.append((
                "CPU Request (m)",
                f"{cpu_req.get('min', 0):.0f}",
                f"{cpu_req.get('avg', 0):.0f}",
                f"{cpu_req.get('max', 0):.0f}",
                f"{cpu_req.get('p95', 0):.0f}",
            ))
        if cpu_lim:
            rows.append((
                "CPU Limit (m)",
                f"{cpu_lim.get('min', 0):.0f}",
                f"{cpu_lim.get('avg', 0):.0f}",
                f"{cpu_lim.get('max', 0):.0f}",
                f"{cpu_lim.get('p95', 0):.0f}",
            ))
        if mem_req:
            mi = 1024 * 1024
            rows.append((
                "Memory Request (Mi)",
                f"{mem_req.get('min', 0) / mi:.0f}",
                f"{mem_req.get('avg', 0) / mi:.0f}",
                f"{mem_req.get('max', 0) / mi:.0f}",
                f"{mem_req.get('p95', 0) / mi:.0f}",
            ))
        if mem_lim:
            mi = 1024 * 1024
            rows.append((
                "Memory Limit (Mi)",
                f"{mem_lim.get('min', 0) / mi:.0f}",
                f"{mem_lim.get('avg', 0) / mi:.0f}",
                f"{mem_lim.get('max', 0) / mi:.0f}",
                f"{mem_lim.get('p95', 0) / mi:.0f}",
            ))
        return rows

    def get_overview_alloc_rows(self) -> list[tuple]:
        """Allocated Analysis rows for the overview DataTable (spec 1.2)."""
        nodes = self.get_nodes()
        if not nodes:
            return []
        # Compute per-node allocation percentages
        cpu_req_pcts: list[float] = []
        mem_req_pcts: list[float] = []
        cpu_lim_pcts: list[float] = []
        mem_lim_pcts: list[float] = []
        for node in nodes:
            cpu_alloc = self._safe_float(getattr(node, "cpu_allocatable", 0))
            mem_alloc = self._safe_float(getattr(node, "memory_allocatable", 0))
            cpu_req = self._safe_float(node.cpu_requests)
            mem_req = self._safe_float(node.memory_requests)
            cpu_lim = self._safe_float(getattr(node, "cpu_limits", 0))
            mem_lim = self._safe_float(getattr(node, "memory_limits", 0))
            if cpu_alloc > 0:
                cpu_req_pcts.append(cpu_req / cpu_alloc * 100)
                cpu_lim_pcts.append(cpu_lim / cpu_alloc * 100)
            if mem_alloc > 0:
                mem_req_pcts.append(mem_req / mem_alloc * 100)
                mem_lim_pcts.append(mem_lim / mem_alloc * 100)
        if not cpu_req_pcts:
            return []

        def _fmt_alloc(v: float) -> str:
            return self._format_alloc_pct(v)

        rows: list[tuple] = []
        rows.append((
            "CPU Req %",
            _fmt_alloc(sum(cpu_req_pcts) / len(cpu_req_pcts)),
            _fmt_alloc(max(cpu_req_pcts)),
            _fmt_alloc(self._percentile(cpu_req_pcts, 95)),
        ))
        rows.append((
            "Mem Req %",
            _fmt_alloc(sum(mem_req_pcts) / len(mem_req_pcts)),
            _fmt_alloc(max(mem_req_pcts)),
            _fmt_alloc(self._percentile(mem_req_pcts, 95)),
        ))
        rows.append((
            "CPU Lim %",
            _fmt_alloc(sum(cpu_lim_pcts) / len(cpu_lim_pcts)),
            _fmt_alloc(max(cpu_lim_pcts)),
            _fmt_alloc(self._percentile(cpu_lim_pcts, 95)),
        ))
        rows.append((
            "Mem Lim %",
            _fmt_alloc(sum(mem_lim_pcts) / len(mem_lim_pcts)),
            _fmt_alloc(max(mem_lim_pcts)),
            _fmt_alloc(self._percentile(mem_lim_pcts, 95)),
        ))
        return rows

    def get_stats_rows(self) -> list[tuple[str, str, str]]:
        rows: list[tuple[str, str, str]] = []
        s = self.get_stats_data()
        rows.append(("Nodes", "Total", str(s.get("total_nodes", 0))))
        rows.append(("Nodes", "Ready", str(s.get("ready_nodes", 0))))
        rows.append(("Nodes", "Not Ready", str(s.get("not_ready_nodes", 0))))
        for etype, count in s.get("event_counts", {}).items():
            rows.append(("Events", etype, str(count)))
        rows.append(("PDBs", "Total", str(s.get("total_pdbs", 0))))
        rows.append(("PDBs", "Blocking", str(s.get("blocking_pdbs", 0))))
        rows.append(("Workloads", "Single Replica", str(s.get("single_replica_count", 0))))
        rows.append(("Workloads", "Total", str(s.get("total_workloads", 0))))
        return rows

    # =========================================================================
    # Text Formatting (Rich markup strings)
    # =========================================================================

    def get_overview_text(self) -> str:
        d = self.get_overview_data()
        lines = [
            f"[b]Cluster Overview:[/b] [#30d158]{d['cluster_name']}[/#30d158]", "",
            f"[b]Nodes:[/b] {d['ready_nodes']}/{d['total_nodes']} Ready",
        ]
        not_ready = d["total_nodes"] - d["ready_nodes"]
        if not_ready:
            lines.append(f"  [bold #ff3b30]{not_ready} Not Ready[/bold #ff3b30]")
        lines.extend(["", f"[b]Events:[/b] {d['total_events']} total",
                       f"  [#ff9f0a]{d['warning_events']} Warnings[/#ff9f0a]",
                       f"  [bold #ff3b30]{d['error_events']} Errors[/bold #ff3b30]", "",
                       f"[b]Pod Disruption Budgets:[/b] {d['total_pdbs']} total"])
        lines.append(
            f"  [bold #ff3b30]{d['blocking_pdbs']} Blocking[/bold #ff3b30]"
            if d["blocking_pdbs"]
            else "  [#30d158]All OK[/#30d158]"
        )
        lines.extend(["", f"[b]Single Replica Workloads:[/b] {d['single_replica_count']}"])
        lines.append(
            "  [#ff9f0a]Review for HA[/#ff9f0a]"
            if d["single_replica_count"]
            else "  [#30d158]All protected[/#30d158]"
        )

        # Nodes Approaching Pod Capacity cross-reference
        high_pod_nodes = self.get_high_pod_count_nodes()
        if high_pod_nodes:
            lines.extend([
                "",
                f"[b][#ff9f0a]{len(high_pod_nodes)} node(s) approaching pod capacity"
                f" -- see Groups tab for details[/#ff9f0a][/b]",
            ])

        return "\n".join(lines)

    def get_health_text(self) -> str:
        status, score, issues = self.get_health_data()
        lines = [f"[b]Cluster Health:[/b] {status}", f"[b]Health Score:[/b] {score}/100", ""]
        if issues:
            lines.append("[b]Issues Detected:[/b]")
            lines.extend(f"  - {i}" for i in issues)
        else:
            lines.append("[#30d158]No issues detected[/#30d158]")
        return "\n".join(lines)

    # =========================================================================
    # Composite Data Methods
    # =========================================================================

    def get_overview_data(self) -> dict[str, Any]:
        nodes = self.get_nodes()
        pdbs = self.get_pdbs()
        node_summary = summarize_nodes(nodes)
        event_counts = self.count_events_by_type()
        total_events = sum(event_counts.values()) if event_counts else 0
        return {
            "cluster_name": self.get_cluster_name(),
            "ready_nodes": node_summary["ready_count"],
            "total_nodes": node_summary["node_count"],
            "total_events": total_events,
            "warning_events": self.count_warning_events(),
            "error_events": self.count_error_events(),
            "total_pdbs": len(pdbs),
            "blocking_pdbs": count_blocking_pdbs(pdbs),
            "single_replica_count": len(self.get_single_replica()),
        }

    def get_stats_data(self) -> dict[str, Any]:
        nodes = self.get_nodes()
        pdbs = self.get_pdbs()
        node_summary = summarize_nodes(nodes)
        return {
            "total_nodes": node_summary["node_count"],
            "ready_nodes": node_summary["ready_count"],
            "not_ready_nodes": node_summary["not_ready_count"],
            "event_counts": self.count_events_by_type(),
            "total_pdbs": len(pdbs),
            "blocking_pdbs": count_blocking_pdbs(pdbs),
            "single_replica_count": len(self.get_single_replica()),
            "total_workloads": len(self.get_all_workloads()),
        }

    # =========================================================================
    # Search Filtering
    # =========================================================================

    def filter_rows(self, rows: list[tuple], query: str) -> list[tuple]:
        """Filter table rows by search query (case-insensitive match on any column)."""
        if not query:
            return rows
        q = query.lower()
        return [row for row in rows if any(q in str(cell).lower() for cell in row)]

    # =========================================================================
    # Backward Compatibility
    # =========================================================================

    # Backward-compatible aliases for tests
    def get_event_rows(self) -> list[tuple]:
        return self.get_event_summary_rows()

    def get_pod_rows(self) -> list[tuple]:
        return self.get_pod_dist_stats_rows()

    def populate_all_tabs(self) -> None:
        """Populate all tabs (delegates to screen's _refresh_all_tabs if available)."""
        if hasattr(self._screen, "_refresh_all_tabs"):
            self._screen._refresh_all_tabs()
