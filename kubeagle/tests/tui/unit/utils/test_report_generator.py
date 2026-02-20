"""Comprehensive unit tests for TUIReportGenerator and collect_report_data.

Tests all public methods, formatting helpers, report generation in all formats
(markdown, JSON), edge cases (empty data, partial data, None values), and
the async collect_report_data function.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kubeagle.constants.enums import NodeStatus, QoSClass, Severity
from kubeagle.models.analysis.violation import ViolationResult
from kubeagle.models.charts.chart_info import ChartInfo
from kubeagle.models.core.node_info import NodeInfo
from kubeagle.models.core.workload_info import SingleReplicaWorkloadInfo
from kubeagle.models.events.event_summary import EventSummary
from kubeagle.models.pdb.pdb_info import PDBInfo
from kubeagle.models.reports.report_data import ReportData
from kubeagle.utils.report_generator import (
    TUIReportGenerator,
    collect_report_data,
)

# =============================================================================
# FIXTURES
# =============================================================================


def _make_node(
    name: str = "node-1",
    status: NodeStatus = NodeStatus.READY,
    node_group: str = "default-worker",
    cpu_alloc: float = 4000.0,
    mem_alloc: float = 16_000_000_000.0,
    cpu_req: float = 2000.0,
    mem_req: float = 8_000_000_000.0,
) -> NodeInfo:
    return NodeInfo(
        name=name,
        status=status,
        node_group=node_group,
        instance_type="m5.large",
        availability_zone="us-east-1a",
        cpu_allocatable=cpu_alloc,
        memory_allocatable=mem_alloc,
        cpu_requests=cpu_req,
        cpu_limits=cpu_req * 1.2,
        memory_requests=mem_req,
        memory_limits=mem_req * 1.5,
        pod_count=50,
        pod_capacity=110,
    )


def _make_chart(
    name: str = "test-chart",
    team: str = "team-alpha",
    qos: QoSClass = QoSClass.BURSTABLE,
    pdb_enabled: bool = True,
    replicas: int | None = 2,
    cpu_request: float = 100.0,
    cpu_limit: float = 200.0,
    memory_request: float = 128_000_000.0,
    memory_limit: float = 256_000_000.0,
) -> ChartInfo:
    return ChartInfo(
        name=name,
        team=team,
        values_file="values.yaml",
        cpu_request=cpu_request,
        cpu_limit=cpu_limit,
        memory_request=memory_request,
        memory_limit=memory_limit,
        qos_class=qos,
        has_liveness=True,
        has_readiness=True,
        has_startup=False,
        has_anti_affinity=True,
        has_topology_spread=False,
        has_topology=False,
        pdb_enabled=pdb_enabled,
        pdb_template_exists=True,
        pdb_min_available=1 if pdb_enabled else None,
        pdb_max_unavailable=None,
        replicas=replicas,
        priority_class=None,
    )


def _make_violation(
    chart_name: str = "test-chart",
    sev: Severity = Severity.WARNING,
    vid: str = "RES005",
) -> ViolationResult:
    return ViolationResult(
        id=vid,
        chart_name=chart_name,
        rule_name="High CPU Limit/Request Ratio",
        rule_id=vid,
        category="resources",
        severity=sev,
        description="CPU limit is 5x the request",
        current_value="500m",
        recommended_value="200m",
        fix_available=True,
    )


def _make_pdb(
    name: str = "test-pdb",
    namespace: str = "default",
    is_blocking: bool = False,
    blocking_reason: str | None = None,
) -> PDBInfo:
    return PDBInfo(
        name=name,
        namespace=namespace,
        kind="Deployment",
        min_available=1,
        max_unavailable=None,
        min_unavailable=None,
        max_available=None,
        current_healthy=2,
        desired_healthy=2,
        expected_pods=2,
        disruptions_allowed=1,
        unhealthy_pod_eviction_policy="IfHealthyBudget",
        is_blocking=is_blocking,
        blocking_reason=blocking_reason,
        conflict_type=None,
    )


def _make_workload(
    name: str = "critical-svc",
    namespace: str = "default",
    helm_release: str | None = "critical-svc",
    chart_name: str | None = "critical-svc",
) -> SingleReplicaWorkloadInfo:
    return SingleReplicaWorkloadInfo(
        name=name,
        namespace=namespace,
        kind="Deployment",
        replicas=1,
        ready_replicas=1,
        helm_release=helm_release,
        chart_name=chart_name,
        status="Ready",
    )


def _make_event_summary(
    oom: int = 2,
    node_not_ready: int = 1,
    failed_sched: int = 5,
    backoff: int = 8,
    unhealthy: int = 3,
    failed_mount: int = 2,
    evicted: int = 4,
) -> EventSummary:
    return EventSummary(
        total_count=oom + node_not_ready + failed_sched + backoff + unhealthy + failed_mount + evicted,
        oom_count=oom,
        node_not_ready_count=node_not_ready,
        failed_scheduling_count=failed_sched,
        backoff_count=backoff,
        unhealthy_count=unhealthy,
        failed_mount_count=failed_mount,
        evicted_count=evicted,
        completed_count=0,
        normal_count=0,
        recent_events=[],
    )


def _make_report_data(
    nodes: list[NodeInfo] | None = None,
    charts: list[ChartInfo] | None = None,
    violations: list[ViolationResult] | None = None,
    pdbs: list[PDBInfo] | None = None,
    workloads: list[SingleReplicaWorkloadInfo] | None = None,
    event_summary: EventSummary | None = None,
    cluster_name: str = "test-cluster",
    context: str | None = "test-context",
    timestamp: str = "2025-01-15 10:00:00 UTC",
) -> ReportData:
    return ReportData(
        nodes=nodes or [],
        event_summary=event_summary,
        pdbs=pdbs or [],
        single_replica_workloads=workloads or [],
        charts=charts or [],
        violations=violations or [],
        cluster_name=cluster_name,
        context=context,
        timestamp=timestamp,
    )


@pytest.fixture
def full_report_data() -> ReportData:
    """Complete report data with all sections populated."""
    nodes = [
        _make_node("node-1", NodeStatus.READY, "group-a"),
        _make_node("node-2", NodeStatus.READY, "group-a"),
        _make_node("node-3", NodeStatus.NOT_READY, "group-b"),
    ]
    charts = [
        _make_chart("frontend", "team-fe", QoSClass.BURSTABLE, True, 3),
        _make_chart("backend", "team-be", QoSClass.GUARANTEED, True, 2),
        _make_chart("worker", "team-fe", QoSClass.BEST_EFFORT, False, 1,
                     cpu_request=0.0, cpu_limit=0.0,
                     memory_request=0.0, memory_limit=0.0),
    ]
    violations = [
        _make_violation("frontend", Severity.WARNING, "RES005"),
        _make_violation("worker", Severity.ERROR, "PRB001"),
    ]
    pdbs = [
        _make_pdb("good-pdb", "default", False),
        _make_pdb("bad-pdb", "kube-system", True, "maxUnavailable=0 blocks all evictions"),
    ]
    workloads = [
        _make_workload("svc-1", "default"),
        _make_workload("svc-2", "legacy", None, None),
    ]
    events = _make_event_summary()
    return _make_report_data(nodes, charts, violations, pdbs, workloads, events)


@pytest.fixture
def empty_report_data() -> ReportData:
    """Report data with all empty/None collections."""
    return _make_report_data()


@pytest.fixture
def gen(full_report_data: ReportData) -> TUIReportGenerator:
    """A generator with full data for convenience."""
    return TUIReportGenerator(data=full_report_data)


@pytest.fixture
def empty_gen(empty_report_data: ReportData) -> TUIReportGenerator:
    """A generator with empty data for convenience."""
    return TUIReportGenerator(data=empty_report_data)


# =============================================================================
# CONSTRUCTOR
# =============================================================================


class TestTUIReportGeneratorInit:
    """Test constructor initialization."""

    def test_init_stores_data(self, full_report_data: ReportData) -> None:
        gen = TUIReportGenerator(data=full_report_data)
        assert gen.data is full_report_data

    def test_init_lines_empty(self, full_report_data: ReportData) -> None:
        gen = TUIReportGenerator(data=full_report_data)
        assert gen.lines == []

    def test_init_class_constants(self) -> None:
        header, sep = TUIReportGenerator.TABLE_HEADER_METRIC_VALUE
        assert "Metric" in header
        assert "Value" in header
        assert "---" in sep


# =============================================================================
# FORMATTING HELPERS
# =============================================================================


class TestFormatCPU:
    """Test _format_cpu method."""

    def test_millicores_below_1000(self, gen: TUIReportGenerator) -> None:
        assert gen._format_cpu(100) == "100m"

    def test_millicores_at_1000(self, gen: TUIReportGenerator) -> None:
        assert gen._format_cpu(1000) == "1.0c"

    def test_millicores_above_1000(self, gen: TUIReportGenerator) -> None:
        assert gen._format_cpu(2500) == "2.5c"

    def test_zero_millicores(self, gen: TUIReportGenerator) -> None:
        assert gen._format_cpu(0) == "0m"

    def test_fractional_millicores(self, gen: TUIReportGenerator) -> None:
        assert gen._format_cpu(99.7) == "100m"

    def test_large_value(self, gen: TUIReportGenerator) -> None:
        assert gen._format_cpu(16000) == "16.0c"


class TestFormatMemory:
    """Test _format_memory method."""

    def test_bytes(self, gen: TUIReportGenerator) -> None:
        assert gen._format_memory(512) == "512B"

    def test_kilobytes(self, gen: TUIReportGenerator) -> None:
        assert gen._format_memory(2048) == "2Ki"

    def test_megabytes(self, gen: TUIReportGenerator) -> None:
        assert gen._format_memory(128 * 1024 * 1024) == "128Mi"

    def test_gigabytes(self, gen: TUIReportGenerator) -> None:
        assert gen._format_memory(2 * 1024**3) == "2.0Gi"

    def test_zero_bytes(self, gen: TUIReportGenerator) -> None:
        assert gen._format_memory(0) == "0B"

    def test_boundary_ki(self, gen: TUIReportGenerator) -> None:
        assert gen._format_memory(1024) == "1Ki"

    def test_boundary_mi(self, gen: TUIReportGenerator) -> None:
        result = gen._format_memory(1024 * 1024)
        assert "Mi" in result

    def test_boundary_gi(self, gen: TUIReportGenerator) -> None:
        result = gen._format_memory(1024**3)
        assert "Gi" in result


class TestFormatRatio:
    """Test _format_ratio method."""

    def test_none_ratio(self, gen: TUIReportGenerator) -> None:
        assert gen._format_ratio(None) == "N/A"

    def test_normal_ratio(self, gen: TUIReportGenerator) -> None:
        assert gen._format_ratio(1.5) == "1.5"

    def test_high_ratio_default_threshold(self, gen: TUIReportGenerator) -> None:
        result = gen._format_ratio(3.0)
        assert "3.0" in result
        assert "[WARN]" in result

    def test_at_threshold(self, gen: TUIReportGenerator) -> None:
        # Exactly at threshold should NOT show warning (> not >=)
        result = gen._format_ratio(2.0, threshold=2.0)
        assert "[WARN]" not in result

    def test_above_threshold(self, gen: TUIReportGenerator) -> None:
        result = gen._format_ratio(2.1, threshold=2.0)
        assert "[WARN]" in result

    def test_custom_threshold(self, gen: TUIReportGenerator) -> None:
        result = gen._format_ratio(5.0, threshold=4.0)
        assert "[WARN]" in result


class TestStatusEmoji:
    """Test _status_emoji method."""

    def test_true_condition(self, gen: TUIReportGenerator) -> None:
        assert gen._status_emoji(True) == "[OK]"

    def test_false_condition_no_warn(self, gen: TUIReportGenerator) -> None:
        assert gen._status_emoji(False) == "[ERR]"

    def test_false_condition_warn(self, gen: TUIReportGenerator) -> None:
        assert gen._status_emoji(False, warn=True) == "[WARN]"


class TestBoolEmoji:
    """Test _bool_emoji method."""

    def test_true(self, gen: TUIReportGenerator) -> None:
        assert gen._bool_emoji(True) == "[OK]"

    def test_false(self, gen: TUIReportGenerator) -> None:
        assert gen._bool_emoji(False) == "[ERR]"


class TestPct:
    """Test _pct method."""

    def test_normal_percentage(self, gen: TUIReportGenerator) -> None:
        assert gen._pct(1, 2) == pytest.approx(50.0)

    def test_zero_total(self, gen: TUIReportGenerator) -> None:
        assert gen._pct(5, 0) == 0.0

    def test_full_percentage(self, gen: TUIReportGenerator) -> None:
        assert gen._pct(10, 10) == pytest.approx(100.0)

    def test_zero_part(self, gen: TUIReportGenerator) -> None:
        assert gen._pct(0, 100) == 0.0


class TestFormatCoverage:
    """Test _format_coverage method."""

    def test_high_coverage(self, gen: TUIReportGenerator) -> None:
        result = gen._format_coverage(85.0)
        assert "85.0%" in result
        assert "[OK]" in result

    def test_medium_coverage(self, gen: TUIReportGenerator) -> None:
        result = gen._format_coverage(60.0)
        assert "60.0%" in result
        assert "[WARN]" in result

    def test_low_coverage(self, gen: TUIReportGenerator) -> None:
        result = gen._format_coverage(30.0)
        assert "30.0%" in result
        assert "[ERR]" in result

    def test_boundary_80(self, gen: TUIReportGenerator) -> None:
        result = gen._format_coverage(80.0)
        assert "[OK]" in result

    def test_boundary_50(self, gen: TUIReportGenerator) -> None:
        result = gen._format_coverage(50.0)
        assert "[WARN]" in result

    def test_zero_coverage(self, gen: TUIReportGenerator) -> None:
        result = gen._format_coverage(0.0)
        assert "[ERR]" in result


# =============================================================================
# INTERNAL LINE HELPERS
# =============================================================================


class TestAddLines:
    """Test _add and _add_lines methods."""

    def test_add_single_line(self, gen: TUIReportGenerator) -> None:
        gen.lines = []
        gen._add("hello")
        assert gen.lines == ["hello"]

    def test_add_empty_line(self, gen: TUIReportGenerator) -> None:
        gen.lines = []
        gen._add()
        assert gen.lines == [""]

    def test_add_lines_multiple(self, gen: TUIReportGenerator) -> None:
        gen.lines = []
        gen._add_lines("a", "b", "c")
        assert gen.lines == ["a", "b", "c"]


# =============================================================================
# MARKDOWN REPORT - FULL FORMAT
# =============================================================================


class TestGenerateMarkdownFull:
    """Test generate_markdown_report with full format."""

    def test_full_report_contains_header(self, gen: TUIReportGenerator) -> None:
        report = gen.generate_markdown_report("full")
        assert "# Unified EKS Cluster & Helm Chart Analysis Report" in report

    def test_full_report_contains_cluster_name(self, gen: TUIReportGenerator) -> None:
        report = gen.generate_markdown_report("full")
        assert "test-cluster" in report

    def test_full_report_contains_timestamp(self, gen: TUIReportGenerator) -> None:
        report = gen.generate_markdown_report("full")
        assert "2025-01-15 10:00:00 UTC" in report

    def test_full_report_contains_executive_summary(self, gen: TUIReportGenerator) -> None:
        report = gen.generate_markdown_report("full")
        assert "## Executive Summary" in report

    def test_full_report_contains_eks_analysis(self, gen: TUIReportGenerator) -> None:
        report = gen.generate_markdown_report("full")
        assert "## 1. EKS Cluster Analysis" in report

    def test_full_report_contains_helm_analysis(self, gen: TUIReportGenerator) -> None:
        report = gen.generate_markdown_report("full")
        assert "## 2. Helm Chart Analysis" in report

    def test_full_report_contains_recommendations(self, gen: TUIReportGenerator) -> None:
        report = gen.generate_markdown_report("full")
        assert "## 3. Recommendations" in report

    def test_full_report_contains_footer(self, gen: TUIReportGenerator) -> None:
        report = gen.generate_markdown_report("full")
        assert "KubEagle TUI v2.0" in report

    def test_full_report_node_data(self, gen: TUIReportGenerator) -> None:
        report = gen.generate_markdown_report("full")
        assert "node-1" in report
        assert "node-2" in report

    def test_full_report_chart_data(self, gen: TUIReportGenerator) -> None:
        report = gen.generate_markdown_report("full")
        assert "frontend" in report
        assert "backend" in report

    def test_full_report_violations_section(self, gen: TUIReportGenerator) -> None:
        report = gen.generate_markdown_report("full")
        assert "### 2.5 Violations Summary" in report
        assert "RES005" in report
        assert "PRB001" in report

    def test_full_report_pdb_section(self, gen: TUIReportGenerator) -> None:
        report = gen.generate_markdown_report("full")
        assert "### 1.3 Pod Disruption Budgets" in report
        assert "bad-pdb" in report

    def test_full_report_single_replica_workloads(self, gen: TUIReportGenerator) -> None:
        report = gen.generate_markdown_report("full")
        assert "### 1.4 Single Replica Workloads" in report
        assert "svc-1" in report

    def test_full_report_node_group_distribution(self, gen: TUIReportGenerator) -> None:
        report = gen.generate_markdown_report("full")
        assert "### 1.5 Node Group Distribution" in report
        assert "group-a" in report

    def test_full_report_qos_distribution(self, gen: TUIReportGenerator) -> None:
        report = gen.generate_markdown_report("full")
        assert "### 2.2 QoS Class Distribution" in report

    def test_full_report_resource_analysis(self, gen: TUIReportGenerator) -> None:
        report = gen.generate_markdown_report("full")
        assert "### 2.4 Resource Analysis" in report

    def test_full_report_blocking_pdb_recommendation(self, gen: TUIReportGenerator) -> None:
        report = gen.generate_markdown_report("full")
        assert "PDBs Blocking Node Drains" in report

    def test_full_report_charts_without_pdb_recommendation(self, gen: TUIReportGenerator) -> None:
        report = gen.generate_markdown_report("full")
        assert "Charts Without PDBs" in report

    def test_full_report_single_replica_recommendation(self, gen: TUIReportGenerator) -> None:
        report = gen.generate_markdown_report("full")
        assert "Single Replica Charts" in report

    def test_full_report_violation_fixes_table(self, gen: TUIReportGenerator) -> None:
        report = gen.generate_markdown_report("full")
        assert "### 3.3 Violation Fixes" in report

    def test_lines_reset_on_each_call(self, gen: TUIReportGenerator) -> None:
        gen.generate_markdown_report("full")
        first_len = len(gen.lines)
        gen.generate_markdown_report("full")
        assert len(gen.lines) == first_len


# =============================================================================
# MARKDOWN REPORT - BRIEF FORMAT
# =============================================================================


class TestGenerateMarkdownBrief:
    """Test generate_markdown_report with brief format."""

    def test_brief_has_executive_summary(self, gen: TUIReportGenerator) -> None:
        report = gen.generate_markdown_report("brief")
        assert "## Executive Summary" in report

    def test_brief_has_eks_brief(self, gen: TUIReportGenerator) -> None:
        report = gen.generate_markdown_report("brief")
        assert "## 1. EKS Cluster Analysis" in report

    def test_brief_has_helm_brief(self, gen: TUIReportGenerator) -> None:
        report = gen.generate_markdown_report("brief")
        assert "## 2. Helm Chart Analysis" in report

    def test_brief_has_recommendations(self, gen: TUIReportGenerator) -> None:
        report = gen.generate_markdown_report("brief")
        assert "## 3. Recommendations" in report

    def test_brief_no_node_group_distribution(self, gen: TUIReportGenerator) -> None:
        report = gen.generate_markdown_report("brief")
        # Brief uses _add_eks_brief not _add_eks_analysis, so no node group dist
        assert "### 1.5 Node Group Distribution" not in report

    def test_brief_no_violations_summary(self, gen: TUIReportGenerator) -> None:
        report = gen.generate_markdown_report("brief")
        assert "### 2.5 Violations Summary" not in report


# =============================================================================
# MARKDOWN REPORT - SUMMARY FORMAT
# =============================================================================


class TestGenerateMarkdownSummary:
    """Test generate_markdown_report with summary format."""

    def test_summary_has_executive_summary(self, gen: TUIReportGenerator) -> None:
        report = gen.generate_markdown_report("summary")
        assert "## Executive Summary" in report

    def test_summary_has_recommendations(self, gen: TUIReportGenerator) -> None:
        report = gen.generate_markdown_report("summary")
        assert "## 2. Recommendations" in report

    def test_summary_no_eks_analysis(self, gen: TUIReportGenerator) -> None:
        report = gen.generate_markdown_report("summary")
        assert "## 1. EKS Cluster Analysis" not in report

    def test_summary_no_helm_analysis(self, gen: TUIReportGenerator) -> None:
        report = gen.generate_markdown_report("summary")
        # Summary should not have the full Helm analysis heading
        # Only executive summary tables and summary recommendations
        assert "## 2. Helm Chart Analysis" not in report

    def test_summary_priority_actions(self, gen: TUIReportGenerator) -> None:
        report = gen.generate_markdown_report("summary")
        assert "### Priority Actions" in report


# =============================================================================
# MARKDOWN REPORT - EMPTY DATA
# =============================================================================


class TestGenerateMarkdownEmpty:
    """Test markdown report with empty data."""

    def test_empty_full_report_has_header(self, empty_gen: TUIReportGenerator) -> None:
        report = empty_gen.generate_markdown_report("full")
        assert "# Unified EKS Cluster & Helm Chart Analysis Report" in report

    def test_empty_no_nodes_message(self, empty_gen: TUIReportGenerator) -> None:
        report = empty_gen.generate_markdown_report("full")
        assert "_No EKS cluster data available._" in report

    def test_empty_no_charts_message(self, empty_gen: TUIReportGenerator) -> None:
        report = empty_gen.generate_markdown_report("full")
        assert "_No Helm chart data available._" in report

    def test_empty_summary_zeros(self, empty_gen: TUIReportGenerator) -> None:
        report = empty_gen.generate_markdown_report("full")
        assert "Total Nodes | 0" in report

    def test_empty_no_blocking_pdbs(self, empty_gen: TUIReportGenerator) -> None:
        report = empty_gen.generate_markdown_report("full")
        assert "No critical EKS issues found" in report

    def test_empty_brief_no_nodes(self, empty_gen: TUIReportGenerator) -> None:
        report = empty_gen.generate_markdown_report("brief")
        assert "_No EKS cluster data available._" in report

    def test_empty_brief_no_charts(self, empty_gen: TUIReportGenerator) -> None:
        report = empty_gen.generate_markdown_report("brief")
        assert "_No Helm chart data available._" in report


# =============================================================================
# MARKDOWN - PARTIAL DATA
# =============================================================================


class TestGenerateMarkdownPartialData:
    """Test markdown report with partial data (some sections empty)."""

    def test_nodes_only(self) -> None:
        data = _make_report_data(nodes=[_make_node()])
        gen = TUIReportGenerator(data=data)
        report = gen.generate_markdown_report("full")
        assert "node-1" in report
        assert "_No Helm chart data available._" in report

    def test_charts_only(self) -> None:
        data = _make_report_data(charts=[_make_chart()])
        gen = TUIReportGenerator(data=data)
        report = gen.generate_markdown_report("full")
        assert "_No EKS cluster data available._" in report
        assert "test-chart" in report

    def test_no_event_summary(self) -> None:
        data = _make_report_data(
            nodes=[_make_node()],
            event_summary=None,
        )
        gen = TUIReportGenerator(data=data)
        report = gen.generate_markdown_report("full")
        # Without events, should show zero OOM
        assert "OOM Events (1h)" in report

    def test_no_violations(self) -> None:
        data = _make_report_data(
            charts=[_make_chart()],
            violations=[],
        )
        gen = TUIReportGenerator(data=data)
        report = gen.generate_markdown_report("full")
        assert "### 2.5 Violations Summary" in report

    def test_workloads_without_helm_release(self) -> None:
        wl = _make_workload("orphan", "ns", None, None)
        data = _make_report_data(
            nodes=[_make_node()],
            workloads=[wl],
        )
        gen = TUIReportGenerator(data=data)
        report = gen.generate_markdown_report("full")
        assert "orphan" in report
        # None helm_release should display as "-"
        assert "| - |" in report

    def test_no_blocking_pdbs_shows_green(self) -> None:
        data = _make_report_data(
            pdbs=[_make_pdb("safe", "ns", False)],
        )
        gen = TUIReportGenerator(data=data)
        report = gen.generate_markdown_report("full")
        assert "No critical EKS issues found" in report

    def test_many_blocking_pdbs_truncates(self) -> None:
        pdbs = [
            _make_pdb(f"blocking-{i}", "ns", True, f"reason {i}")
            for i in range(10)
        ]
        data = _make_report_data(pdbs=pdbs)
        gen = TUIReportGenerator(data=data)
        report = gen.generate_markdown_report("full")
        assert "... and 5 more" in report


# =============================================================================
# JSON REPORT
# =============================================================================


class TestGenerateJsonReport:
    """Test generate_json_report method."""

    def test_json_full_is_valid(self, gen: TUIReportGenerator) -> None:
        result = gen.generate_json_report("full")
        data = json.loads(result)
        assert isinstance(data, dict)

    def test_json_full_has_metadata(self, gen: TUIReportGenerator) -> None:
        data = json.loads(gen.generate_json_report("full"))
        assert "metadata" in data
        assert data["metadata"]["cluster"] == "test-cluster"
        assert data["metadata"]["context"] == "test-context"
        assert data["metadata"]["format"] == "full"

    def test_json_full_has_summary(self, gen: TUIReportGenerator) -> None:
        data = json.loads(gen.generate_json_report("full"))
        assert "summary" in data
        summary = data["summary"]
        assert summary["total_charts"] == 3
        assert summary["total_nodes"] == 3

    def test_json_full_has_cluster(self, gen: TUIReportGenerator) -> None:
        data = json.loads(gen.generate_json_report("full"))
        assert "cluster" in data
        assert len(data["cluster"]["nodes"]) == 3

    def test_json_full_has_charts(self, gen: TUIReportGenerator) -> None:
        data = json.loads(gen.generate_json_report("full"))
        assert "charts" in data
        assert data["charts"]["total_charts"] == 3

    def test_json_full_has_violations(self, gen: TUIReportGenerator) -> None:
        data = json.loads(gen.generate_json_report("full"))
        assert "violations" in data
        assert len(data["violations"]) == 2

    def test_json_full_has_recommendations(self, gen: TUIReportGenerator) -> None:
        data = json.loads(gen.generate_json_report("full"))
        assert "recommendations" in data
        assert isinstance(data["recommendations"], list)

    def test_json_summary_no_cluster(self, gen: TUIReportGenerator) -> None:
        data = json.loads(gen.generate_json_report("summary"))
        assert "cluster" not in data
        assert "charts" not in data

    def test_json_summary_has_summary(self, gen: TUIReportGenerator) -> None:
        data = json.loads(gen.generate_json_report("summary"))
        assert "summary" in data

    def test_json_brief_has_cluster_and_charts(self, gen: TUIReportGenerator) -> None:
        data = json.loads(gen.generate_json_report("brief"))
        assert "cluster" in data
        assert "charts" in data

    def test_json_brief_no_violations(self, gen: TUIReportGenerator) -> None:
        data = json.loads(gen.generate_json_report("brief"))
        assert "violations" not in data

    def test_json_empty_data(self, empty_gen: TUIReportGenerator) -> None:
        data = json.loads(empty_gen.generate_json_report("full"))
        assert data["summary"]["total_charts"] == 0
        assert data["summary"]["total_nodes"] == 0
        # No nodes, so no cluster key
        assert "cluster" not in data

    def test_json_chart_details(self, gen: TUIReportGenerator) -> None:
        data = json.loads(gen.generate_json_report("full"))
        chart_list = data["charts"]["charts"]
        names = {c["name"] for c in chart_list}
        assert "frontend" in names
        assert "backend" in names

    def test_json_violation_details(self, gen: TUIReportGenerator) -> None:
        data = json.loads(gen.generate_json_report("full"))
        v = data["violations"][0]
        assert "id" in v
        assert "severity" in v
        assert "description" in v
        assert "fix_available" in v


# =============================================================================
# GET DICT HELPERS
# =============================================================================


class TestGetSummaryDict:
    """Test _get_summary_dict method."""

    def test_summary_dict_keys(self, gen: TUIReportGenerator) -> None:
        summary = gen._get_summary_dict()
        expected_keys = {
            "total_charts", "total_nodes", "total_violations",
            "error_violations", "warning_violations",
            "charts_with_pdb", "single_replica_charts",
            "single_replica_workloads", "blocking_pdbs",
        }
        assert set(summary.keys()) == expected_keys

    def test_summary_dict_values(self, gen: TUIReportGenerator) -> None:
        summary = gen._get_summary_dict()
        assert summary["total_charts"] == 3
        assert summary["total_nodes"] == 3
        assert summary["total_violations"] == 2
        assert summary["error_violations"] == 1
        assert summary["warning_violations"] == 1
        assert summary["charts_with_pdb"] == 2
        assert summary["single_replica_charts"] == 1
        assert summary["single_replica_workloads"] == 2
        assert summary["blocking_pdbs"] == 1

    def test_summary_dict_empty(self, empty_gen: TUIReportGenerator) -> None:
        summary = empty_gen._get_summary_dict()
        assert summary["total_charts"] == 0
        assert summary["blocking_pdbs"] == 0


class TestGetClusterDict:
    """Test _get_cluster_dict method."""

    def test_cluster_dict_nodes(self, gen: TUIReportGenerator) -> None:
        cluster = gen._get_cluster_dict()
        assert len(cluster["nodes"]) == 3
        node = cluster["nodes"][0]
        assert "name" in node
        assert "status" in node
        assert "cpu_allocatable" in node

    def test_cluster_dict_event_summary(self, gen: TUIReportGenerator) -> None:
        cluster = gen._get_cluster_dict()
        events = cluster["event_summary"]
        assert events["oom_count"] == 2

    def test_cluster_dict_pdbs(self, gen: TUIReportGenerator) -> None:
        cluster = gen._get_cluster_dict()
        assert len(cluster["pdbs"]) == 2

    def test_cluster_dict_workloads(self, gen: TUIReportGenerator) -> None:
        cluster = gen._get_cluster_dict()
        assert len(cluster["single_replica_workloads"]) == 2

    def test_cluster_dict_no_events(self, empty_gen: TUIReportGenerator) -> None:
        cluster = empty_gen._get_cluster_dict()
        assert cluster["event_summary"] == {}


class TestGetChartsDict:
    """Test _get_charts_dict method."""

    def test_charts_dict_total(self, gen: TUIReportGenerator) -> None:
        charts = gen._get_charts_dict()
        assert charts["total_charts"] == 3

    def test_charts_dict_by_team(self, gen: TUIReportGenerator) -> None:
        charts = gen._get_charts_dict()
        assert "team-fe" in charts["by_team"]
        assert charts["by_team"]["team-fe"] == 2

    def test_charts_dict_by_qos(self, gen: TUIReportGenerator) -> None:
        charts = gen._get_charts_dict()
        assert "Burstable" in charts["by_qos"]

    def test_charts_dict_single_replica_count(self, gen: TUIReportGenerator) -> None:
        charts = gen._get_charts_dict()
        assert charts["single_replica_count"] == 1

    def test_charts_dict_chart_details(self, gen: TUIReportGenerator) -> None:
        charts = gen._get_charts_dict()
        assert len(charts["charts"]) == 3
        c = charts["charts"][0]
        required = {
            "name", "team", "qos_class", "replicas",
            "cpu_request", "cpu_limit", "memory_request", "memory_limit",
            "has_liveness", "has_readiness", "has_startup",
            "has_anti_affinity", "has_topology_spread", "pdb_enabled",
        }
        assert required.issubset(set(c.keys()))


class TestGetViolationsDict:
    """Test _get_violations_dict method."""

    def test_violations_list_length(self, gen: TUIReportGenerator) -> None:
        violations = gen._get_violations_dict()
        assert len(violations) == 2

    def test_violation_entry_fields(self, gen: TUIReportGenerator) -> None:
        v = gen._get_violations_dict()[0]
        required = {
            "id", "chart_name", "rule_name", "severity",
            "description", "current_value", "recommended_value", "fix_available",
        }
        assert required.issubset(set(v.keys()))

    def test_empty_violations(self, empty_gen: TUIReportGenerator) -> None:
        assert empty_gen._get_violations_dict() == []


class TestGetRecommendationsList:
    """Test _get_recommendations_list method."""

    def test_has_blocking_pdb_recommendation(self, gen: TUIReportGenerator) -> None:
        recs = gen._get_recommendations_list()
        assert any("Fix blocking PDB" in r for r in recs)

    def test_has_enable_pdb_recommendation(self, gen: TUIReportGenerator) -> None:
        recs = gen._get_recommendations_list()
        assert any("Enable PDB" in r for r in recs)

    def test_has_single_replica_recommendation(self, gen: TUIReportGenerator) -> None:
        recs = gen._get_recommendations_list()
        assert any("increasing replicas" in r for r in recs)

    def test_has_violation_recommendations(self, gen: TUIReportGenerator) -> None:
        recs = gen._get_recommendations_list()
        assert any("[ERROR]" in r or "[WARNING]" in r for r in recs)

    def test_empty_recommendations(self, empty_gen: TUIReportGenerator) -> None:
        recs = empty_gen._get_recommendations_list()
        assert recs == []

    def test_recommendations_limit_pdb(self) -> None:
        """Charts without PDB recommendations capped at 5."""
        charts = [
            _make_chart(f"chart-{i}", "team", pdb_enabled=False)
            for i in range(10)
        ]
        data = _make_report_data(charts=charts)
        gen = TUIReportGenerator(data=data)
        recs = gen._get_recommendations_list()
        enable_pdb_recs = [r for r in recs if "Enable PDB" in r]
        assert len(enable_pdb_recs) == 5

    def test_recommendations_limit_single_replica(self) -> None:
        """Single replica recommendations capped at 5."""
        charts = [
            _make_chart(f"chart-{i}", "team", replicas=1)
            for i in range(10)
        ]
        data = _make_report_data(charts=charts)
        gen = TUIReportGenerator(data=data)
        recs = gen._get_recommendations_list()
        replica_recs = [r for r in recs if "increasing replicas" in r]
        assert len(replica_recs) == 5

    def test_recommendations_limit_violations(self) -> None:
        """Violation recommendations capped at 10."""
        violations = [_make_violation(f"chart-{i}", vid=f"V{i:03d}") for i in range(20)]
        data = _make_report_data(violations=violations)
        gen = TUIReportGenerator(data=data)
        recs = gen._get_recommendations_list()
        violation_recs = [r for r in recs if "[WARNING]" in r]
        assert len(violation_recs) <= 10


# =============================================================================
# EXECUTIVE SUMMARY EDGE CASES
# =============================================================================


class TestExecutiveSummaryEdgeCases:
    """Test executive summary with specific edge cases."""

    def test_all_nodes_healthy(self) -> None:
        nodes = [_make_node(f"n-{i}") for i in range(3)]
        data = _make_report_data(nodes=nodes)
        gen = TUIReportGenerator(data=data)
        report = gen.generate_markdown_report("full")
        # All healthy should show an OK status marker beside count.
        assert "[OK] 3" in report

    def test_some_nodes_not_ready(self) -> None:
        nodes = [
            _make_node("n-1"),
            _make_node("n-2", NodeStatus.NOT_READY),
        ]
        data = _make_report_data(nodes=nodes)
        gen = TUIReportGenerator(data=data)
        report = gen.generate_markdown_report("full")
        # Not all healthy: warning
        assert "Healthy Nodes" in report

    def test_no_event_summary_shows_zero(self) -> None:
        data = _make_report_data(event_summary=None)
        gen = TUIReportGenerator(data=data)
        report = gen.generate_markdown_report("full")
        assert "OOM Events (1h)" in report


# =============================================================================
# BRIEF EKS SECTION - EVENT SUMMARY
# =============================================================================


class TestBriefEksEventSummary:
    """Test event summary in brief EKS section."""

    def test_events_present(self) -> None:
        events = _make_event_summary(oom=5)
        data = _make_report_data(nodes=[_make_node()], event_summary=events)
        gen = TUIReportGenerator(data=data)
        report = gen.generate_markdown_report("brief")
        assert "OOMKilling" in report
        assert "| 5 |" in report

    def test_events_none(self) -> None:
        data = _make_report_data(nodes=[_make_node()], event_summary=None)
        gen = TUIReportGenerator(data=data)
        report = gen.generate_markdown_report("brief")
        assert "No events data" in report


# =============================================================================
# SUMMARY RECOMMENDATIONS EDGE CASES
# =============================================================================


class TestSummaryRecommendationsSection:
    """Test the summary recommendations section."""

    def test_with_violations_shows_counts(self) -> None:
        violations = [
            _make_violation("c1", Severity.ERROR, "E001"),
            _make_violation("c2", Severity.WARNING, "W001"),
            _make_violation("c3", Severity.WARNING, "W002"),
        ]
        data = _make_report_data(violations=violations)
        gen = TUIReportGenerator(data=data)
        report = gen.generate_markdown_report("summary")
        assert "Errors: 1" in report
        assert "Warnings: 2" in report

    def test_without_violations(self) -> None:
        data = _make_report_data()
        gen = TUIReportGenerator(data=data)
        report = gen.generate_markdown_report("summary")
        assert "Charts with Violations: 0" in report


# =============================================================================
# HELM BRIEF SECTION
# =============================================================================


class TestHelmBriefSection:
    """Test _add_helm_brief section details."""

    def test_team_distribution(self) -> None:
        charts = [
            _make_chart("c1", "team-x"),
            _make_chart("c2", "team-x"),
            _make_chart("c3", "team-y"),
        ]
        data = _make_report_data(charts=charts)
        gen = TUIReportGenerator(data=data)
        report = gen.generate_markdown_report("brief")
        assert "team-x" in report
        assert "| 2 |" in report

    def test_qos_distribution(self) -> None:
        charts = [
            _make_chart("c1", qos=QoSClass.GUARANTEED),
            _make_chart("c2", qos=QoSClass.BURSTABLE),
        ]
        data = _make_report_data(charts=charts)
        gen = TUIReportGenerator(data=data)
        report = gen.generate_markdown_report("brief")
        assert "Guaranteed" in report
        assert "Burstable" in report
        assert "BestEffort" in report

    def test_resource_analysis_caps_at_50(self) -> None:
        charts = [_make_chart(f"chart-{i:03d}") for i in range(60)]
        data = _make_report_data(charts=charts)
        gen = TUIReportGenerator(data=data)
        report = gen.generate_markdown_report("brief")
        # The table should show at most 50 charts
        chart_rows = [line for line in report.split("\n") if "chart-" in line and "|" in line]
        # Resource analysis section caps at 50
        assert len(chart_rows) <= 60  # brief has multiple sections with charts


# =============================================================================
# COLLECT REPORT DATA (ASYNC)
# =============================================================================


class TestCollectReportData:
    """Test the async collect_report_data function."""

    @pytest.mark.asyncio
    async def test_no_controllers(self) -> None:
        result = await collect_report_data(
            cluster_controller=None,
            charts_controller=None,
            optimizer_controller=None,
            charts_path=None,
            context=None,
        )
        assert isinstance(result, ReportData)
        assert result.nodes == []
        assert result.charts == []
        assert result.violations == []
        assert result.cluster_name == "Unknown"

    @pytest.mark.asyncio
    async def test_cluster_controller_connection_failure(self) -> None:
        mock_ctrl = AsyncMock()
        mock_ctrl.check_cluster_connection = AsyncMock(side_effect=Exception("timeout"))
        result = await collect_report_data(
            cluster_controller=mock_ctrl,
            charts_controller=None,
            optimizer_controller=None,
            charts_path=None,
            context=None,
        )
        assert result.nodes == []
        assert result.cluster_name == "Unknown"

    @pytest.mark.asyncio
    async def test_cluster_controller_not_connected(self) -> None:
        mock_ctrl = AsyncMock()
        mock_ctrl.check_cluster_connection = AsyncMock(return_value=False)
        result = await collect_report_data(
            cluster_controller=mock_ctrl,
            charts_controller=None,
            optimizer_controller=None,
            charts_path=None,
            context=None,
        )
        assert result.nodes == []

    @pytest.mark.asyncio
    async def test_cluster_data_collection_timeout(self) -> None:
        mock_ctrl = AsyncMock()
        mock_ctrl.check_cluster_connection = AsyncMock(return_value=True)

        # Simulate a timeout by patching asyncio.wait_for to raise TimeoutError
        # rather than actually sleeping
        mock_ctrl.fetch_nodes = AsyncMock(return_value=[])
        mock_ctrl.get_event_summary = AsyncMock(return_value=None)
        mock_ctrl.fetch_pdbs = AsyncMock(return_value=[])
        mock_ctrl.fetch_single_replica_workloads = AsyncMock(return_value=[])

        async def mock_wait_for(coro: object, *, timeout: float) -> object:
            # Cancel the coro and raise TimeoutError
            if hasattr(coro, "close"):
                coro.close()  # type: ignore[union-attr]
            raise asyncio.TimeoutError()

        with (
            patch("subprocess.run") as mock_run,
            patch(
                "kubeagle.utils.report_generator.asyncio.wait_for",
                side_effect=mock_wait_for,
            ),
        ):
            mock_run.return_value = MagicMock(
                stdout="Kubernetes control plane running at https://test-cluster.example.com:6443\n",
                returncode=0,
            )
            result = await collect_report_data(
                cluster_controller=mock_ctrl,
                charts_controller=None,
                optimizer_controller=None,
                charts_path=None,
                context="test",
            )
        assert result.nodes == []

    @pytest.mark.asyncio
    async def test_charts_controller_success(self) -> None:
        mock_charts_ctrl = AsyncMock()
        mock_charts_ctrl.analyze_all_charts_async = AsyncMock(
            return_value=[_make_chart()]
        )
        result = await collect_report_data(
            cluster_controller=None,
            charts_controller=mock_charts_ctrl,
            optimizer_controller=None,
            charts_path="/path/to/charts",
            context=None,
        )
        assert len(result.charts) == 1

    @pytest.mark.asyncio
    async def test_charts_controller_error(self) -> None:
        mock_charts_ctrl = AsyncMock()
        mock_charts_ctrl.analyze_all_charts_async = AsyncMock(
            side_effect=Exception("parse error")
        )
        result = await collect_report_data(
            cluster_controller=None,
            charts_controller=mock_charts_ctrl,
            optimizer_controller=None,
            charts_path="/path/to/charts",
            context=None,
        )
        assert result.charts == []

    @pytest.mark.asyncio
    async def test_charts_controller_no_path(self) -> None:
        mock_charts_ctrl = AsyncMock()
        result = await collect_report_data(
            cluster_controller=None,
            charts_controller=mock_charts_ctrl,
            optimizer_controller=None,
            charts_path=None,
            context=None,
        )
        # charts_path is None so charts_controller should NOT be called
        assert result.charts == []
        mock_charts_ctrl.analyze_all_charts_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_optimizer_controller_with_charts(self) -> None:
        charts = [_make_chart()]
        mock_charts_ctrl = AsyncMock()
        mock_charts_ctrl.analyze_all_charts_async = AsyncMock(return_value=charts)
        mock_optimizer = MagicMock()
        mock_optimizer.check_all_charts = MagicMock(
            return_value=[_make_violation()]
        )
        result = await collect_report_data(
            cluster_controller=None,
            charts_controller=mock_charts_ctrl,
            optimizer_controller=mock_optimizer,
            charts_path="/charts",
            context=None,
        )
        assert len(result.violations) == 1

    @pytest.mark.asyncio
    async def test_optimizer_not_called_without_charts(self) -> None:
        mock_optimizer = MagicMock()
        result = await collect_report_data(
            cluster_controller=None,
            charts_controller=None,
            optimizer_controller=mock_optimizer,
            charts_path=None,
            context=None,
        )
        assert result.violations == []
        mock_optimizer.check_all_charts.assert_not_called()

    @pytest.mark.asyncio
    async def test_result_has_timestamp(self) -> None:
        result = await collect_report_data(
            cluster_controller=None,
            charts_controller=None,
            optimizer_controller=None,
            charts_path=None,
            context=None,
        )
        assert "UTC" in result.timestamp

    @pytest.mark.asyncio
    async def test_context_passed_through(self) -> None:
        result = await collect_report_data(
            cluster_controller=None,
            charts_controller=None,
            optimizer_controller=None,
            charts_path=None,
            context="my-cluster-ctx",
        )
        assert result.context == "my-cluster-ctx"

    @pytest.mark.asyncio
    async def test_cluster_name_extraction(self) -> None:
        mock_ctrl = AsyncMock()
        mock_ctrl.check_cluster_connection = AsyncMock(return_value=True)
        mock_ctrl.fetch_nodes = AsyncMock(return_value=[])
        mock_ctrl.get_event_summary = AsyncMock(return_value=None)
        mock_ctrl.fetch_pdbs = AsyncMock(return_value=[])
        mock_ctrl.fetch_single_replica_workloads = AsyncMock(return_value=[])

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="Kubernetes control plane is running at https://my-cluster.us-east-1.eks.amazonaws.com:6443\n",
                returncode=0,
            )
            result = await collect_report_data(
                cluster_controller=mock_ctrl,
                charts_controller=None,
                optimizer_controller=None,
                charts_path=None,
                context=None,
            )
        assert "my-cluster" in result.cluster_name

    @pytest.mark.asyncio
    async def test_cluster_name_with_context(self) -> None:
        mock_ctrl = AsyncMock()
        mock_ctrl.check_cluster_connection = AsyncMock(return_value=True)
        mock_ctrl.fetch_nodes = AsyncMock(return_value=[])
        mock_ctrl.get_event_summary = AsyncMock(return_value=None)
        mock_ctrl.fetch_pdbs = AsyncMock(return_value=[])
        mock_ctrl.fetch_single_replica_workloads = AsyncMock(return_value=[])

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="Kubernetes control plane is running at https://staging.example.com:6443\n",
                returncode=0,
            )
            result = await collect_report_data(
                cluster_controller=mock_ctrl,
                charts_controller=None,
                optimizer_controller=None,
                charts_path=None,
                context="staging",
            )
        # When context is provided, it should be passed to kubectl
        assert result.cluster_name != "Unknown"

    @pytest.mark.asyncio
    async def test_cluster_data_collection_error(self) -> None:
        mock_ctrl = AsyncMock()
        mock_ctrl.check_cluster_connection = AsyncMock(return_value=True)
        mock_ctrl.fetch_nodes = AsyncMock(side_effect=RuntimeError("api error"))
        mock_ctrl.get_event_summary = AsyncMock(return_value=None)
        mock_ctrl.fetch_pdbs = AsyncMock(return_value=[])
        mock_ctrl.fetch_single_replica_workloads = AsyncMock(return_value=[])

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="nothing here\n",
                returncode=1,
            )
            result = await collect_report_data(
                cluster_controller=mock_ctrl,
                charts_controller=None,
                optimizer_controller=None,
                charts_path=None,
                context=None,
            )
        # Error in gather should leave nodes empty
        assert result.nodes == []
