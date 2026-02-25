"""Resource impact calculator for before/after optimization comparison."""

from __future__ import annotations

import json
import logging
import math
import subprocess
from pathlib import PurePosixPath
from typing import Any

from kubeagle.constants.instance_types import (
    ALLOCATABLE_RATIO,
    DEFAULT_INSTANCE_TYPES,
    DEFAULT_OVERHEAD_PCT,
    HOURS_PER_MONTH,
    SPOT_PRICES,
)
from kubeagle.models.charts.chart_info import ChartInfo
from kubeagle.models.optimization.resource_impact import (
    ChartResourceSnapshot,
    ClusterNodeGroup,
    FleetResourceSummary,
    InstanceTypeSpec,
    NodeEstimation,
    ResourceDelta,
    ResourceImpactResult,
)
import kubeagle.optimizer.rules as _optimizer_rules
from kubeagle.optimizer.rules import _parse_cpu
from kubeagle.utils.resource_parser import memory_str_to_bytes

logger = logging.getLogger(__name__)


def fetch_workload_replica_map(
    context: str | None = None,
    timeout: int = 30,
) -> dict[tuple[str, str], int]:
    """Fetch actual desired replica counts from the cluster.

    Runs a lightweight ``kubectl get deployments,statefulsets`` to retrieve
    the actual ``spec.replicas`` for each workload, keyed by
    ``(workload_name, namespace)``.

    Uses the workload's ``metadata.name`` (the actual Deployment/StatefulSet
    name) as the key — NOT the Helm release label.  This prevents umbrella
    charts from inflating counts: sub-chart workloads have distinct names
    (e.g. ``contact-service-redis``) and won't be summed into the parent
    chart's entry (``contact-service``).

    Returns:
        Mapping of ``(workload_name, namespace) -> desired_replicas``.
    """
    cmd = ["kubectl"]
    if context:
        cmd.extend(["--context", context])
    cmd.extend([
        "get", "deployments,statefulsets",
        "-A", "-o", "json",
        f"--request-timeout={timeout}s",
    ])

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout + 5,
        )
        if result.returncode != 0:
            logger.warning("kubectl workload fetch failed: %s", (result.stderr or "").strip())
            return {}
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        logger.warning("kubectl workload fetch error: %s", exc)
        return {}

    try:
        data = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError):
        return {}

    replica_map: dict[tuple[str, str], int] = {}
    for item in data.get("items", []):
        metadata = item.get("metadata", {})
        spec = item.get("spec", {})
        workload_name = metadata.get("name", "")
        namespace = metadata.get("namespace", "")

        if not workload_name or not namespace:
            continue

        desired = spec.get("replicas", 1)
        try:
            desired = int(desired)
        except (TypeError, ValueError):
            desired = 1

        map_key = (workload_name, namespace)
        # Sum in case of duplicate names (e.g. Deployment + StatefulSet
        # with the same name, which is rare but possible).
        replica_map[map_key] = replica_map.get(map_key, 0) + desired

    return replica_map


def _deduplicate_charts_by_name(
    charts: list[ChartInfo],
) -> list[ChartInfo]:
    """Keep one representative ChartInfo per unique ``(name, namespace, parent_chart)``.

    Local charts (no namespace) with the same name but different values
    files are collapsed into one entry — prefers ``values.yaml`` (main).
    Cluster charts with different namespaces remain separate.
    Umbrella sub-charts with the same alias but different parents are kept
    separate (e.g. two ``redis`` sub-charts from different umbrella charts).
    """
    by_key: dict[tuple[str, str, str], ChartInfo] = {}
    for chart in charts:
        key = (chart.name, chart.namespace or "", chart.parent_chart or "")
        if key not in by_key:
            by_key[key] = chart
        else:
            # Prefer "values.yaml" (Main)
            current_vf = str(getattr(by_key[key], "values_file", "") or "").strip()
            if PurePosixPath(current_vf).name.lower() != "values.yaml":
                candidate_vf = str(getattr(chart, "values_file", "") or "").strip()
                if PurePosixPath(candidate_vf).name.lower() == "values.yaml":
                    by_key[key] = chart
    return list(by_key.values())


# Rule IDs that change CPU/memory values
RESOURCE_RULE_IDS: set[str] = {
    "RES002",
    "RES003",
    "RES004",
    "RES005",
    "RES006",
    "RES007",
    "RES008",
    "RES009",
}

# Rule IDs that change replica count
REPLICA_RULE_IDS: set[str] = {"AVL005"}

# All rule IDs that affect resource impact
IMPACT_RULE_IDS: set[str] = RESOURCE_RULE_IDS | REPLICA_RULE_IDS

# Application order: request-setting rules first, then limit-setting rules.
# This ensures that limit rules (RES002, RES003, RES005, RES006) see the
# already-updated request values from (RES004, RES007, RES008, RES009).
_RULE_PRIORITY: dict[str, int] = {
    # Phase 1 — set/bump requests
    "RES004": 0,  # Add missing requests + limits (requests first)
    "RES007": 1,  # Bump low CPU request
    "RES008": 1,  # Add missing memory request
    "RES009": 1,  # Bump low memory request
    # Phase 2 — set/adjust limits (relative to requests)
    "RES002": 2,  # Add CPU limit (2× request)
    "RES003": 2,  # Add memory limit (2× request)
    "RES005": 2,  # Reduce high CPU limit/request ratio
    "RES006": 2,  # Reduce high memory limit/request ratio
    # Phase 3 — replicas
    "AVL005": 3,  # Increase replica count
}


def _build_instance_types(
    raw_types: list[tuple[str, int, float, float, float]] | None = None,
) -> list[InstanceTypeSpec]:
    """Build InstanceTypeSpec list from raw tuples."""
    source = raw_types or DEFAULT_INSTANCE_TYPES
    specs: list[InstanceTypeSpec] = []
    for name, vcpus, memory_gib, price, spot_price in source:
        specs.append(
            InstanceTypeSpec(
                name=name,
                vcpus=vcpus,
                memory_gib=memory_gib,
                cpu_millicores=vcpus * 1000,
                memory_bytes=int(memory_gib * 1024**3),
                hourly_price_usd=price,
                spot_price_usd=spot_price,
            )
        )
    return specs


class ResourceImpactCalculator:
    """Computes before/after resource impact for a fleet of charts."""

    def compute_impact(
        self,
        charts: list[ChartInfo],
        violations: list[Any],
        *,
        overhead_pct: float = DEFAULT_OVERHEAD_PCT,
        instance_types: list[tuple[str, int, float, float, float]] | None = None,
        optimizer_controller: Any | None = None,
        cluster_nodes: list[Any] | None = None,
        workload_replica_map: dict[tuple[str, str], int] | None = None,
    ) -> ResourceImpactResult:
        """Compute the full resource impact analysis.

        Args:
            charts: List of ChartInfo objects.
            violations: List of ViolationResult objects.
            overhead_pct: System overhead percentage (0.0-1.0).
            instance_types: Optional custom instance type specs (fallback).
            optimizer_controller: Optional UnifiedOptimizerController for fix generation.
            cluster_nodes: Optional list of NodeInfo from the live cluster.
            workload_replica_map: Optional mapping of (release_name, namespace) to
                actual desired replica counts from the cluster.  When provided the
                calculator uses real replica counts instead of values-file defaults.

        Returns:
            ResourceImpactResult with before/after summaries, delta, and node estimations.
        """
        specs = _build_instance_types(instance_types)

        # Deduplicate charts by name (merge multiple values-file variants)
        charts = _deduplicate_charts_by_name(charts)

        # Group violations by (chart_name, parent_chart), only resource/replica rules.
        # Including parent_chart prevents umbrella sub-charts with the same alias
        # (e.g. two ``redis`` from different parents) from mixing violations.
        violations_by_chart: dict[tuple[str, str], list[Any]] = {}
        for v in violations:
            rule_id = getattr(v, "rule_id", "") or getattr(v, "id", "")
            if rule_id in IMPACT_RULE_IDS:
                chart_name = getattr(v, "chart_name", "")
                parent_chart = getattr(v, "parent_chart", "") or ""
                violations_by_chart.setdefault(
                    (chart_name, parent_chart), [],
                ).append(v)

        before_charts: list[ChartResourceSnapshot] = []
        after_charts: list[ChartResourceSnapshot] = []

        for chart in charts:
            before = self._build_before_snapshot(chart, workload_replica_map)
            before_charts.append(before)

            chart_violations = violations_by_chart.get(
                (chart.name, chart.parent_chart or ""), [],
            )
            after = self._compute_after_snapshot(
                chart,
                chart_violations,
                optimizer_controller=optimizer_controller,
                workload_replica_map=workload_replica_map,
            )
            after_charts.append(after)

        before_summary = self._aggregate(before_charts)
        after_summary = self._aggregate(after_charts)
        delta = self._compute_delta(before_summary, after_summary)

        # Estimate nodes from hardcoded instance types (fallback)
        node_estimations = self._estimate_nodes(
            before_summary, after_summary, specs, overhead_pct
        )

        # Estimate from real cluster nodes when available
        cluster_node_groups: list[ClusterNodeGroup] = []
        if cluster_nodes:
            cluster_node_groups = self._estimate_from_cluster_nodes(
                after_summary, cluster_nodes, overhead_pct
            )

        # Total spot savings from whichever source is active
        if cluster_node_groups:
            total_savings = sum(g.cost_savings_monthly for g in cluster_node_groups)
        else:
            total_savings = sum(e.cost_savings_monthly for e in node_estimations)

        return ResourceImpactResult(
            before=before_summary,
            after=after_summary,
            delta=delta,
            before_charts=before_charts,
            after_charts=after_charts,
            node_estimations=node_estimations,
            cluster_node_groups=cluster_node_groups,
            total_spot_savings_monthly=total_savings,
        )

    def _build_before_snapshot(
        self,
        chart: ChartInfo,
        workload_replica_map: dict[tuple[str, str], int] | None = None,
    ) -> ChartResourceSnapshot:
        """Build a resource snapshot from current chart values.

        When *workload_replica_map* is provided the actual cluster replica
        count is used instead of the values-file default.  The map key is
        ``(release_name, namespace)``; the chart's ``name`` and ``namespace``
        are used for the lookup.
        """
        total_replicas, release_count, min_rep, max_rep = self._resolve_replicas(
            chart, workload_replica_map,
        )
        cpu_req = chart.cpu_request  # already millicores
        cpu_lim = chart.cpu_limit
        mem_req = chart.memory_request  # already bytes
        mem_lim = chart.memory_limit

        return ChartResourceSnapshot(
            name=chart.name,
            parent_chart=chart.parent_chart or "",
            team=chart.team,
            replicas=total_replicas,
            release_count=release_count,
            min_replicas=min_rep,
            max_replicas=max_rep,
            cpu_request_per_replica=cpu_req,
            cpu_limit_per_replica=cpu_lim,
            memory_request_per_replica=mem_req,
            memory_limit_per_replica=mem_lim,
            cpu_request_total=cpu_req * total_replicas,
            cpu_limit_total=cpu_lim * total_replicas,
            memory_request_total=mem_req * total_replicas,
            memory_limit_total=mem_lim * total_replicas,
        )

    def _compute_after_snapshot(
        self,
        chart: ChartInfo,
        chart_violations: list[Any],
        *,
        optimizer_controller: Any | None = None,
        workload_replica_map: dict[tuple[str, str], int] | None = None,
    ) -> ChartResourceSnapshot:
        """Compute the after-optimization snapshot for a chart.

        Applies fix dicts from the optimizer controller to compute new values.
        Falls back to parsing violation recommended_value if controller unavailable.
        """
        # Track both values-file replicas and actual cluster total so that
        # replica fixes can be applied as a proportional scaling ratio.
        values_replicas = max(1, chart.replicas or 1)
        total_replicas, release_count, min_rep, max_rep = self._resolve_replicas(
            chart, workload_replica_map,
        )
        # Start with cluster-aware total replicas (same as before snapshot)
        replicas = total_replicas
        cpu_req = chart.cpu_request
        cpu_lim = chart.cpu_limit
        mem_req = chart.memory_request
        mem_lim = chart.memory_limit

        # Sort violations so request-setting rules run before limit-setting
        # rules. This prevents limit rules from using stale request values.
        sorted_violations = sorted(
            chart_violations,
            key=lambda v: _RULE_PRIORITY.get(
                getattr(v, "rule_id", "") or getattr(v, "id", ""), 99
            ),
        )

        # Track the replica scaling ratio so min/max can be scaled proportionally.
        replica_ratio = 1.0

        for violation in sorted_violations:
            rule_id = getattr(violation, "rule_id", "") or getattr(violation, "id", "")

            # Try to get fix dict from controller
            fix_dict = None
            if optimizer_controller is not None:
                try:
                    fix_dict = optimizer_controller.generate_fix(chart, violation)
                except Exception:
                    logger.debug(
                        "Failed to generate fix for %s/%s", chart.name, rule_id
                    )

            if fix_dict and rule_id in RESOURCE_RULE_IDS:
                cpu_req, cpu_lim, mem_req, mem_lim = self._apply_resource_fix(
                    fix_dict, cpu_req, cpu_lim, mem_req, mem_lim
                )
            elif rule_id in RESOURCE_RULE_IDS and fix_dict is None:
                # Fallback: apply default fix values for known rules
                cpu_req, cpu_lim, mem_req, mem_lim = self._apply_default_resource_fix(
                    rule_id, cpu_req, cpu_lim, mem_req, mem_lim
                )

            if rule_id in REPLICA_RULE_IDS:
                if fix_dict and "replicaCount" in fix_dict:
                    fix_target = max(1, int(fix_dict["replicaCount"]))
                    # Apply as proportional scaling: if values goes 1→2 and
                    # cluster has 7 total, after = 7 × (2/1) = 14.
                    if total_replicas > values_replicas and values_replicas > 0:
                        ratio = fix_target / values_replicas
                        replicas = max(replicas, int(total_replicas * ratio))
                        replica_ratio = max(replica_ratio, ratio)
                    else:
                        replicas = max(replicas, fix_target)
                        if values_replicas > 0:
                            replica_ratio = max(replica_ratio, fix_target / values_replicas)
                elif values_replicas < 2:
                    if total_replicas > values_replicas and values_replicas > 0:
                        ratio = 2 / values_replicas
                        replicas = max(replicas, int(total_replicas * ratio))
                        replica_ratio = max(replica_ratio, ratio)
                    else:
                        replicas = 2
                        replica_ratio = max(replica_ratio, 2.0 / max(values_replicas, 1))

        # Scale min/max proportionally when replicas changed
        after_min = max(1, int(min_rep * replica_ratio)) if replica_ratio > 1.0 else min_rep
        after_max = max(1, int(max_rep * replica_ratio)) if replica_ratio > 1.0 else max_rep

        # Ensure limits are never less than requests (fixes can be applied
        # in an order that makes them inconsistent, e.g. RES005 reduces
        # the limit based on the old request, then RES007 bumps the request).
        if cpu_lim > 0 and cpu_lim < cpu_req:
            cpu_lim = cpu_req * 1.5
        if mem_lim > 0 and mem_lim < mem_req:
            mem_lim = mem_req * 1.5

        return ChartResourceSnapshot(
            name=chart.name,
            parent_chart=chart.parent_chart or "",
            team=chart.team,
            replicas=replicas,
            release_count=release_count,
            min_replicas=after_min,
            max_replicas=after_max,
            cpu_request_per_replica=cpu_req,
            cpu_limit_per_replica=cpu_lim,
            memory_request_per_replica=mem_req,
            memory_limit_per_replica=mem_lim,
            cpu_request_total=cpu_req * replicas,
            cpu_limit_total=cpu_lim * replicas,
            memory_request_total=mem_req * replicas,
            memory_limit_total=mem_lim * replicas,
        )

    @staticmethod
    def _resolve_replicas(
        chart: ChartInfo,
        workload_replica_map: dict[tuple[str, str], int] | None,
    ) -> tuple[int, int, int, int]:
        """Resolve total replica count, release count, min and max for a chart.

        For cluster charts (namespace set): exact ``(name, namespace)`` lookup,
        returns ``(replicas, 1, replicas, replicas)``.

        For local charts (no namespace): scans all entries matching the chart
        name across namespaces and returns the **actual sum** of replicas
        (not an average) to avoid precision loss from integer division.

        Returns:
            ``(total_replicas, release_count, min_replicas, max_replicas)``
        """
        values_replicas = max(1, chart.replicas or 1)
        namespace = chart.namespace or ""

        if not workload_replica_map:
            return values_replicas, 1, values_replicas, values_replicas

        if namespace:
            # Cluster chart: exact lookup
            cluster_replicas = workload_replica_map.get((chart.name, namespace))
            if cluster_replicas is not None and cluster_replicas > 0:
                return cluster_replicas, 1, cluster_replicas, cluster_replicas
        else:
            # Local chart: sum actual replicas across all matching releases.
            total_replicas = 0
            total_releases = 0
            per_release: list[int] = []
            for (rel_name, _ns), rep in workload_replica_map.items():
                if rel_name == chart.name:
                    total_replicas += rep
                    total_releases += 1
                    per_release.append(rep)
            if total_releases > 0 and total_replicas > 0:
                return total_replicas, total_releases, min(per_release), max(per_release)

        # No cluster data — single release with values-file replicas
        return values_replicas, 1, values_replicas, values_replicas

    @staticmethod
    def _apply_resource_fix(
        fix_dict: dict[str, Any],
        cpu_req: float,
        cpu_lim: float,
        mem_req: float,
        mem_lim: float,
    ) -> tuple[float, float, float, float]:
        """Apply a fix dict's resource changes to current values."""
        resources = fix_dict.get("resources", {})
        requests = resources.get("requests", {})
        limits = resources.get("limits", {})
        fixed = _optimizer_rules.FIXED_RESOURCE_FIELDS

        if "cpu" in requests and "cpu_request" not in fixed:
            parsed = _parse_cpu(requests["cpu"])
            if parsed is not None:
                cpu_req = parsed
        if "cpu" in limits and "cpu_limit" not in fixed:
            parsed = _parse_cpu(limits["cpu"])
            if parsed is not None:
                cpu_lim = parsed
        if "memory" in requests and "memory_request" not in fixed:
            parsed_bytes = memory_str_to_bytes(str(requests["memory"]))
            if parsed_bytes > 0:
                mem_req = parsed_bytes
        if "memory" in limits and "memory_limit" not in fixed:
            parsed_bytes = memory_str_to_bytes(str(limits["memory"]))
            if parsed_bytes > 0:
                mem_lim = parsed_bytes

        return cpu_req, cpu_lim, mem_req, mem_lim

    @staticmethod
    def _apply_default_resource_fix(
        rule_id: str,
        cpu_req: float,
        cpu_lim: float,
        mem_req: float,
        mem_lim: float,
    ) -> tuple[float, float, float, float]:
        """Apply default fix values when optimizer controller is not available."""
        fixed = _optimizer_rules.FIXED_RESOURCE_FIELDS
        if rule_id == "RES002":
            # No CPU limit -> set to 2x request or 500m
            if "cpu_limit" not in fixed:
                cpu_lim = max(cpu_req * 2, 500.0) if cpu_req > 0 else 500.0
        elif rule_id == "RES003":
            # No memory limit -> set to 2x request or 512Mi
            if "memory_limit" not in fixed:
                mem_lim = max(mem_req * 2, 512 * 1024**2) if mem_req > 0 else 512 * 1024**2
        elif rule_id == "RES004":
            # No requests -> add defaults
            if cpu_req == 0 and "cpu_request" not in fixed:
                cpu_req = 100.0
            if mem_req == 0 and "memory_request" not in fixed:
                mem_req = 128 * 1024**2
            if cpu_lim == 0 and "cpu_limit" not in fixed:
                cpu_lim = 500.0
            if mem_lim == 0 and "memory_limit" not in fixed:
                mem_lim = 512 * 1024**2
        elif rule_id == "RES005":
            # High CPU ratio — increase request to bring ratio to 1.5x.
            # Limits are never decreased.
            if cpu_lim > 0 and "cpu_request" not in fixed:
                cpu_req = cpu_lim / 1.5
        elif rule_id == "RES006":
            # High memory ratio — increase request to bring ratio to 1.5x.
            # Limits are never decreased.
            if mem_lim > 0 and "memory_request" not in fixed:
                mem_req = mem_lim / 1.5
        elif rule_id == "RES007":
            # Very low CPU request -> bump to 100m (exempt from fixed fields)
            cpu_req = max(cpu_req, 100.0)
        elif rule_id == "RES008":
            # No memory request -> add 128Mi
            if mem_req == 0 and "memory_request" not in fixed:
                mem_req = 128 * 1024**2
        elif rule_id == "RES009":
            # Very low memory request -> bump to 128Mi (exempt from fixed fields)
            mem_req = max(mem_req, 128 * 1024**2)

        return cpu_req, cpu_lim, mem_req, mem_lim

    @staticmethod
    def _aggregate(snapshots: list[ChartResourceSnapshot]) -> FleetResourceSummary:
        """Sum resource totals across all chart snapshots."""
        cpu_req = 0.0
        cpu_lim = 0.0
        mem_req = 0.0
        mem_lim = 0.0
        total_replicas = 0
        total_releases = 0

        for snap in snapshots:
            cpu_req += snap.cpu_request_total
            cpu_lim += snap.cpu_limit_total
            mem_req += snap.memory_request_total
            mem_lim += snap.memory_limit_total
            total_replicas += snap.replicas
            total_releases += snap.release_count

        return FleetResourceSummary(
            cpu_request_total=cpu_req,
            cpu_limit_total=cpu_lim,
            memory_request_total=mem_req,
            memory_limit_total=mem_lim,
            chart_count=len(snapshots),
            total_replicas=total_replicas,
            total_releases=total_releases,
        )

    @staticmethod
    def _compute_delta(
        before: FleetResourceSummary,
        after: FleetResourceSummary,
    ) -> ResourceDelta:
        """Compute the difference between before and after summaries."""

        def _pct(old: float, new: float) -> float:
            if old == 0:
                return 0.0 if new == 0 else 100.0
            return ((new - old) / old) * 100.0

        return ResourceDelta(
            cpu_request_diff=after.cpu_request_total - before.cpu_request_total,
            cpu_limit_diff=after.cpu_limit_total - before.cpu_limit_total,
            memory_request_diff=after.memory_request_total - before.memory_request_total,
            memory_limit_diff=after.memory_limit_total - before.memory_limit_total,
            cpu_request_pct=_pct(before.cpu_request_total, after.cpu_request_total),
            cpu_limit_pct=_pct(before.cpu_limit_total, after.cpu_limit_total),
            memory_request_pct=_pct(before.memory_request_total, after.memory_request_total),
            memory_limit_pct=_pct(before.memory_limit_total, after.memory_limit_total),
            replicas_diff=after.total_replicas - before.total_replicas,
            replicas_pct=_pct(
                float(before.total_replicas), float(after.total_replicas)
            ),
        )

    @staticmethod
    def _estimate_nodes(
        before: FleetResourceSummary,
        after: FleetResourceSummary,
        instance_types: list[InstanceTypeSpec],
        overhead_pct: float,
    ) -> list[NodeEstimation]:
        """Estimate node counts per instance type before and after optimization."""
        estimations: list[NodeEstimation] = []

        for spec in instance_types:
            usable_cpu = spec.cpu_millicores * ALLOCATABLE_RATIO * (1 - overhead_pct)
            usable_mem = spec.memory_bytes * ALLOCATABLE_RATIO * (1 - overhead_pct)

            if usable_cpu <= 0 or usable_mem <= 0:
                continue

            nodes_before = max(
                math.ceil(before.cpu_request_total / usable_cpu),
                math.ceil(before.memory_request_total / usable_mem),
                1,
            )
            nodes_after = max(
                math.ceil(after.cpu_request_total / usable_cpu),
                math.ceil(after.memory_request_total / usable_mem),
                1,
            )

            reduction = nodes_before - nodes_after
            reduction_pct = (
                (reduction / nodes_before * 100.0) if nodes_before > 0 else 0.0
            )

            cost_before = nodes_before * spec.spot_price_usd * HOURS_PER_MONTH
            cost_after = nodes_after * spec.spot_price_usd * HOURS_PER_MONTH

            estimations.append(
                NodeEstimation(
                    instance_type=spec.name,
                    vcpus=spec.vcpus,
                    memory_gib=spec.memory_gib,
                    nodes_before=nodes_before,
                    nodes_after=nodes_after,
                    reduction=reduction,
                    reduction_pct=reduction_pct,
                    spot_price_usd=spec.spot_price_usd,
                    cost_before_monthly=cost_before,
                    cost_after_monthly=cost_after,
                    cost_savings_monthly=cost_before - cost_after,
                )
            )

        return estimations

    @staticmethod
    def _estimate_from_cluster_nodes(
        after: FleetResourceSummary,
        cluster_nodes: list[Any],
        overhead_pct: float,
    ) -> list[ClusterNodeGroup]:
        """Estimate node needs using real cluster node data.

        Groups nodes by instance_type, then estimates how many nodes of each
        type would be needed after optimization (proportional allocation).
        """
        # Single pass: group nodes by instance type and accumulate totals.
        groups: dict[str, list[Any]] = {}
        group_cpu_totals: dict[str, float] = {}
        group_mem_totals: dict[str, float] = {}
        total_cluster_cpu = 0.0
        total_cluster_mem = 0.0

        for node in cluster_nodes:
            itype = getattr(node, "instance_type", "") or "unknown"
            groups.setdefault(itype, []).append(node)
            cpu_alloc = getattr(node, "cpu_allocatable", 0.0)
            mem_alloc = getattr(node, "memory_allocatable", 0.0)
            group_cpu_totals[itype] = group_cpu_totals.get(itype, 0.0) + cpu_alloc
            group_mem_totals[itype] = group_mem_totals.get(itype, 0.0) + mem_alloc
            total_cluster_cpu += cpu_alloc
            total_cluster_mem += mem_alloc

        if not groups:
            return []

        result: list[ClusterNodeGroup] = []
        for itype, nodes in sorted(groups.items()):
            node_count = len(nodes)
            # Use pre-computed group totals instead of re-summing per group.
            cpu_total = group_cpu_totals[itype]
            mem_total = group_mem_totals[itype]
            cpu_per_node = cpu_total / node_count
            mem_per_node = mem_total / node_count

            # Usable capacity after overhead
            usable_cpu_per_node = cpu_per_node * (1 - overhead_pct)
            usable_mem_per_node = mem_per_node * (1 - overhead_pct)

            if usable_cpu_per_node <= 0 or usable_mem_per_node <= 0:
                continue

            # Proportional share of after-optimization workload for this group
            cpu_share = (cpu_total / total_cluster_cpu) if total_cluster_cpu > 0 else 0.0
            mem_share = (mem_total / total_cluster_mem) if total_cluster_mem > 0 else 0.0

            group_cpu_needed = after.cpu_request_total * cpu_share
            group_mem_needed = after.memory_request_total * mem_share

            nodes_needed = max(
                math.ceil(group_cpu_needed / usable_cpu_per_node),
                math.ceil(group_mem_needed / usable_mem_per_node),
                1,
            )

            reduction = node_count - nodes_needed
            reduction_pct = (reduction / node_count * 100.0) if node_count > 0 else 0.0

            # Look up spot price from known prices
            spot_price = SPOT_PRICES.get(itype, 0.0)
            cost_current = node_count * spot_price * HOURS_PER_MONTH
            cost_after = nodes_needed * spot_price * HOURS_PER_MONTH

            result.append(
                ClusterNodeGroup(
                    instance_type=itype,
                    node_count=node_count,
                    cpu_allocatable_per_node=cpu_per_node,
                    memory_allocatable_per_node=mem_per_node,
                    cpu_allocatable_total=cpu_total,
                    memory_allocatable_total=mem_total,
                    nodes_needed_after=nodes_needed,
                    reduction=reduction,
                    reduction_pct=reduction_pct,
                    spot_price_usd=spot_price,
                    cost_current_monthly=cost_current,
                    cost_after_monthly=cost_after,
                    cost_savings_monthly=cost_current - cost_after,
                )
            )

        return result
