"""Unified optimization rules engine.

This module contains the UnifiedOptimizerController which provides
optimization rule checking for Kubernetes resources.

Moved from: controllers/optimizer_controller.py
"""

from __future__ import annotations

import logging
import os
import shutil
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, TypedDict

from pydantic import BaseModel, PrivateAttr
from typing_extensions import NotRequired

from kubeagle.constants.enums import Severity
from kubeagle.models.analysis.violation import ViolationResult
from kubeagle.models.charts.chart_info import ChartInfo
from kubeagle.optimizer.fixer import FixGenerator
from kubeagle.optimizer.helm_renderer import render_chart
from kubeagle.optimizer.rendered_rule_input import (
    build_rule_inputs_from_rendered,
)
from kubeagle.optimizer.rules import (
    RULES,
    OptimizationViolation as RuleViolation,
    get_rule_by_id,
)
from kubeagle.utils.resource_parser import memory_str_to_bytes, parse_cpu

logger = logging.getLogger(__name__)


class ContainerDict(TypedDict):
    """Type definition for container dict used by optimizer rules.

    Attributes:
        name: Name of the container.
        livenessProbe: Optional liveness probe configuration.
        readinessProbe: Optional readiness probe configuration.
        startupProbe: Optional startup probe configuration.
    """

    name: str
    livenessProbe: NotRequired[dict[str, Any]]
    readinessProbe: NotRequired[dict[str, Any]]
    startupProbe: NotRequired[dict[str, Any]]


class UnifiedOptimizerController(BaseModel):
    """Unified optimization rules engine using rules from optimizer/rules.py.

    This controller checks Kubernetes resources against a set of predefined
    optimization rules and generates violation reports with fix suggestions.

    Attributes:
        rules: List of optimization rules to check against.
    """

    rules: list = RULES
    analysis_source: str = "auto"  # auto|rendered|values
    render_timeout_seconds: int = 30
    max_workers: int = 0
    _helm_available: bool | None = PrivateAttr(default=None)
    _helm_unavailable_logged: bool = PrivateAttr(default=False)

    @staticmethod
    def _format_cpu_millicores(cpu_millicores: float) -> str:
        """Format CPU millicores for rule input and UI text."""
        value = float(cpu_millicores)
        if value.is_integer():
            return f"{int(value)}m"
        formatted = f"{value:.3f}".rstrip("0").rstrip(".")
        return f"{formatted}m"

    @staticmethod
    def _memory_bytes_to_mib(memory_bytes: float) -> float:
        """Convert memory bytes to Mi."""
        return float(memory_bytes) / (1024**2)

    @classmethod
    def _format_memory_mib_from_bytes(cls, memory_bytes: float) -> str:
        """Format memory bytes as Mi for rule input and UI text."""
        memory_mib = cls._memory_bytes_to_mib(memory_bytes)
        rounded = round(memory_mib)
        if abs(memory_mib - rounded) < 1e-6:
            return f"{int(rounded)}Mi"
        formatted = f"{memory_mib:.2f}".rstrip("0").rstrip(".")
        return f"{formatted}Mi"

    def _chart_info_to_dict(self, chart: ChartInfo) -> dict[str, Any]:
        """Convert ChartInfo Pydantic model to dict format expected by optimizer rules.

        Args:
            chart: The ChartInfo model to convert.

        Returns:
            Dictionary representation suitable for rule checking.
        """
        chart_dict: dict[str, Any] = {
            "chart_name": chart.name,
            "qos_class": chart.qos_class.value,
            "resources": {
                "requests": {},
                "limits": {},
            },
            "containers": [],
            "topologySpreadConstraints": [],
            "securityContext": {},
        }

        # Add resources
        if chart.cpu_request > 0:
            chart_dict["resources"]["requests"]["cpu"] = self._format_cpu_millicores(
                chart.cpu_request
            )
        if chart.memory_request > 0:
            chart_dict["resources"]["requests"]["memory"] = (
                self._format_memory_mib_from_bytes(chart.memory_request)
            )
        if chart.cpu_limit > 0:
            chart_dict["resources"]["limits"]["cpu"] = self._format_cpu_millicores(
                chart.cpu_limit
            )
        if chart.memory_limit > 0:
            chart_dict["resources"]["limits"]["memory"] = (
                self._format_memory_mib_from_bytes(chart.memory_limit)
            )

        # Add probe flags at root level for rule detection (#8)
        if chart.has_liveness:
            chart_dict["livenessProbe"] = {}
        if chart.has_readiness:
            chart_dict["readinessProbe"] = {}
        if chart.has_startup:
            chart_dict["startupProbe"] = {}

        # Add container probes (kept for FixGenerator compatibility)
        container: ContainerDict = {"name": chart.name}
        if chart.has_liveness:
            container["livenessProbe"] = {}
        if chart.has_readiness:
            container["readinessProbe"] = {}
        if chart.has_startup:
            container["startupProbe"] = {}
        chart_dict["containers"] = [container] if container else []

        # Add topology spread
        if chart.has_topology_spread:
            chart_dict["topologySpreadConstraints"] = [{}]

        # Add replicas for all charts (needed by single-replica and anti-affinity rules)
        if chart.replicas is not None:
            chart_dict["replicas"] = chart.replicas
            chart_dict["has_anti_affinity"] = chart.has_anti_affinity

        # Add PDB info
        if chart.pdb_enabled:
            chart_dict["pdb_enabled"] = True
            pdb_dict: dict[str, Any] = {}
            if chart.pdb_min_available is not None:
                pdb_dict["minAvailable"] = chart.pdb_min_available
            if chart.pdb_max_unavailable is not None:
                pdb_dict["maxUnavailable"] = chart.pdb_max_unavailable
            chart_dict["podDisruptionBudget"] = pdb_dict

        return chart_dict

    def _derive_current_value(
        self,
        violation: RuleViolation,
        chart: ChartInfo,
        *,
        rendered_rule_input: dict[str, Any] | None = None,
    ) -> str:
        """Derive the current value from chart data based on violation category."""
        rid = violation.rule_id
        qos_label = chart.qos_class.value
        cpu_request = chart.cpu_request
        cpu_limit = chart.cpu_limit
        memory_request = chart.memory_request
        memory_limit = chart.memory_limit

        if rendered_rule_input:
            rendered_qos = rendered_rule_input.get("qos_class")
            if rendered_qos is not None:
                rendered_qos_text = str(rendered_qos).strip()
                if rendered_qos_text:
                    qos_label = rendered_qos_text
            rendered_cpu_request = self._rendered_cpu_millicores(
                rendered_rule_input,
                section="requests",
            )
            rendered_cpu_limit = self._rendered_cpu_millicores(
                rendered_rule_input,
                section="limits",
            )
            rendered_memory_request = self._rendered_memory_bytes(
                rendered_rule_input,
                section="requests",
            )
            rendered_memory_limit = self._rendered_memory_bytes(
                rendered_rule_input,
                section="limits",
            )
            if self._has_rendered_resource_key(
                rendered_rule_input,
                section="requests",
                resource="cpu",
            ):
                cpu_request = rendered_cpu_request or 0.0
            elif rendered_cpu_request is not None:
                cpu_request = rendered_cpu_request

            if self._has_rendered_resource_key(
                rendered_rule_input,
                section="limits",
                resource="cpu",
            ):
                cpu_limit = rendered_cpu_limit or 0.0
            elif rendered_cpu_limit is not None:
                cpu_limit = rendered_cpu_limit

            if self._has_rendered_resource_key(
                rendered_rule_input,
                section="requests",
                resource="memory",
            ):
                memory_request = rendered_memory_request or 0.0
            elif rendered_memory_request is not None:
                memory_request = rendered_memory_request

            if self._has_rendered_resource_key(
                rendered_rule_input,
                section="limits",
                resource="memory",
            ):
                memory_limit = rendered_memory_limit or 0.0
            elif rendered_memory_limit is not None:
                memory_limit = rendered_memory_limit

        # Resource rules - show actual resource values
        if rid == "RES002":
            return (
                "No CPU limit"
                if cpu_limit == 0
                else self._format_cpu_millicores(cpu_limit)
            )
        if rid == "RES003":
            return (
                "No memory limit"
                if memory_limit == 0
                else self._format_memory_mib_from_bytes(memory_limit)
            )
        if rid == "RES004":
            return "No requests"
        if rid == "RES005":
            if cpu_limit > 0 and cpu_request > 0:
                ratio = cpu_limit / cpu_request
                return (
                    f"CPU: {self._format_cpu_millicores(cpu_request)} req / "
                    f"{self._format_cpu_millicores(cpu_limit)} lim "
                    f"({ratio:.1f}x, {qos_label})"
                )
            return f"CPU: {self._format_cpu_millicores(cpu_request)}"
        if rid == "RES007":
            return (
                f"CPU: {self._format_cpu_millicores(cpu_request)} req / "
                f"{self._format_cpu_millicores(cpu_limit)} lim"
                if cpu_limit > 0
                else f"CPU: {self._format_cpu_millicores(cpu_request)}"
            )
        if rid == "RES006":
            if memory_limit > 0 and memory_request > 0:
                ratio = memory_limit / memory_request
                return (
                    f"Mem: {self._format_memory_mib_from_bytes(memory_request)} req / "
                    f"{self._format_memory_mib_from_bytes(memory_limit)} lim "
                    f"({ratio:.1f}x, {qos_label})"
                )
            return f"Mem: {self._format_memory_mib_from_bytes(memory_request)}"
        if rid == "RES009":
            return (
                "Memory: "
                f"{self._format_memory_mib_from_bytes(memory_request)} "
                "(below threshold)"
            )
        if rid == "RES008":
            return "No memory request"
        # Probe rules
        if rid == "PRB001":
            return "No liveness probe" if not chart.has_liveness else "Configured"
        if rid == "PRB002":
            return "No readiness probe" if not chart.has_readiness else "Configured"
        if rid == "PRB003":
            return "No startup probe" if not chart.has_startup else "Configured"
        # Availability rules
        if rid == "AVL001":
            return "No PDB" if not chart.pdb_enabled else "PDB enabled"
        if rid == "AVL002":
            return "No anti-affinity" if not chart.has_anti_affinity else "Configured"
        if rid == "AVL003":
            return f"PDB: min={chart.pdb_min_available} max_unavail={chart.pdb_max_unavailable}"
        if rid == "AVL004":
            return "No topology spread" if not chart.has_topology_spread else "Configured"
        if rid == "AVL005":
            return f"replicas: {chart.replicas}"
        # Security rules
        if rid == "SEC001":
            return "runAsUser: 0"
        return "Not configured"

    def _derive_recommended_value(self, violation: RuleViolation) -> str:
        """Derive recommended value from the rule's fix_preview dict."""
        if violation.rule_id == "RES005":
            return "CPU 1.5-2x req (Burstable) or req=limit (Guaranteed)"
        if violation.rule_id == "RES006":
            return "Mem 1.5-2x req (Burstable) or req=limit (Guaranteed)"
        if not violation.fix_preview:
            return "See description"
        # Flatten fix_preview to a readable string
        parts: list[str] = []
        self._flatten_dict(violation.fix_preview, parts)
        result = ", ".join(parts)
        return result[:56] if len(result) > 56 else result

    def _flatten_dict(
        self, d: dict[str, Any], parts: list[str], prefix: str = ""
    ) -> None:
        """Recursively flatten a dict into 'key: value' strings."""
        for k, v in d.items():
            key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                self._flatten_dict(v, parts, key)
            elif isinstance(v, list):
                parts.append(f"{key}: [...]")
            else:
                parts.append(f"{key}: {v}")

    def _to_violation(
        self,
        violation: RuleViolation,
        chart: ChartInfo,
        *,
        analysis_source: str = "values",
        analysis_note: str = "",
        rendered_rule_input: dict[str, Any] | None = None,
    ) -> ViolationResult:
        """Convert optimizer/rules.py violation to models/types.py violation.

        Args:
            violation: The rule violation to convert.
            chart: The ChartInfo that triggered the violation.

        Returns:
            ViolationResult model suitable for display.
        """
        return ViolationResult(
            id=violation.rule_id,
            chart_name=chart.name,
            parent_chart=chart.parent_chart,
            chart_path=chart.values_file,
            team=chart.team,
            rule_name=violation.name,
            rule_id=violation.rule_id,
            category=violation.category,
            severity=Severity(violation.severity),
            description=violation.description,
            current_value=self._derive_current_value(
                violation,
                chart,
                rendered_rule_input=rendered_rule_input,
            ),
            recommended_value=self._derive_recommended_value(violation),
            fix_available=violation.auto_fixable,
            analysis_source=analysis_source,
            analysis_note=analysis_note,
        )

    def check_chart(self, chart: ChartInfo) -> list[ViolationResult]:
        """Check a chart against all rules from optimizer/rules.py.

        Args:
            chart: The ChartInfo to check.

        Returns:
            List of violations found.
        """
        mode = str(self.analysis_source or "auto").strip().lower()
        if self._should_try_rendered_analysis(mode):
            rendered_violations = self._check_chart_rendered(chart)
            if rendered_violations is not None:
                return rendered_violations

        violations: list[ViolationResult] = []

        # Convert ChartInfo to dict format expected by optimizer rules
        chart_dict = self._chart_info_to_dict(chart)

        # Run all rule checks
        for rule in self.rules:
            try:
                rule_violations = rule.check(chart_dict)
            except Exception:
                logger.warning(
                    "Rule check failed for rule '%s'",
                    rule.id,
                    exc_info=True,
                )
                continue
            violations.extend(
                self._to_violation(
                    v,
                    chart,
                    analysis_source="values",
                    analysis_note="Analyzed from values file content.",
                )
                for v in rule_violations
            )

        return violations

    def _should_try_rendered_analysis(self, mode: str) -> bool:
        """Return whether rendered checks should run for the current mode."""
        if mode not in {"auto", "rendered"}:
            return False
        if self._is_helm_available():
            return True
        if not self._helm_unavailable_logged:
            logger.debug(
                "Skipping rendered optimizer checks because helm binary is unavailable.",
            )
            self._helm_unavailable_logged = True
        return False

    def _is_helm_available(self) -> bool:
        """Resolve and cache helm binary availability for this controller."""
        if self._helm_available is not None:
            return self._helm_available
        self._helm_available = shutil.which("helm") is not None
        return self._helm_available

    def _check_chart_rendered(self, chart: ChartInfo) -> list[ViolationResult] | None:
        """Run optimizer checks on rendered manifests.

        Returns None when rendered analysis is unavailable so caller can fallback.
        """
        values_file = str(chart.values_file or "")
        if not values_file or values_file.startswith("cluster:"):
            return None

        values_path = Path(values_file).expanduser().resolve()
        if not values_path.exists():
            return None
        chart_dir = values_path.parent
        if not (chart_dir / "Chart.yaml").exists():
            return None

        render_result = render_chart(
            chart_dir=chart_dir,
            values_file=values_path,
            release_name=chart.name,
            timeout_seconds=self.render_timeout_seconds,
        )
        if not render_result.ok:
            return None

        rule_inputs = build_rule_inputs_from_rendered(
            render_result.docs,
            chart_name=chart.name,
        )
        if not rule_inputs:
            return []

        violations: list[ViolationResult] = []
        for rule in self.rules:
            matched_violation: RuleViolation | None = None
            matched_rule_input: dict[str, Any] | None = None
            try:
                for rule_input in rule_inputs:
                    candidate = rule.check(rule_input)
                    if candidate:
                        matched_violation = candidate[0]
                        matched_rule_input = rule_input
                        break
            except Exception:
                logger.warning(
                    "Rendered rule check failed for rule '%s'",
                    rule.id,
                    exc_info=True,
                )
                continue

            if matched_violation is None:
                continue
            violations.append(
                self._to_violation(
                    matched_violation,
                    chart,
                    analysis_source="rendered",
                    analysis_note="Analyzed from `helm template` rendered manifests.",
                    rendered_rule_input=matched_rule_input,
                )
            )

        return violations

    @staticmethod
    def _rendered_resource_value(
        rendered_rule_input: dict[str, Any],
        *,
        section: str,
        resource: str,
    ) -> str | None:
        resources = rendered_rule_input.get("resources")
        if not isinstance(resources, dict):
            return None
        section_payload = resources.get(section)
        if not isinstance(section_payload, dict):
            return None
        raw = section_payload.get(resource)
        if raw is None:
            return None
        text = str(raw).strip()
        return text if text else None

    @staticmethod
    def _has_rendered_resource_key(
        rendered_rule_input: dict[str, Any],
        *,
        section: str,
        resource: str,
    ) -> bool:
        resources = rendered_rule_input.get("resources")
        if not isinstance(resources, dict):
            return False
        section_payload = resources.get(section)
        if not isinstance(section_payload, dict):
            return False
        return resource in section_payload

    @classmethod
    def _rendered_cpu_millicores(
        cls,
        rendered_rule_input: dict[str, Any],
        *,
        section: str,
    ) -> float | None:
        cpu_value = cls._rendered_resource_value(
            rendered_rule_input,
            section=section,
            resource="cpu",
        )
        if cpu_value is None:
            return None
        cores = parse_cpu(cpu_value)
        if cores <= 0:
            return None
        return cores * 1000

    @classmethod
    def _rendered_memory_bytes(
        cls,
        rendered_rule_input: dict[str, Any],
        *,
        section: str,
    ) -> float | None:
        memory_value = cls._rendered_resource_value(
            rendered_rule_input,
            section=section,
            resource="memory",
        )
        if memory_value is None:
            return None
        bytes_value = memory_str_to_bytes(memory_value)
        if bytes_value <= 0:
            return None
        return bytes_value

    def check_all_charts(self, charts: list[ChartInfo]) -> list[ViolationResult]:
        """Check all charts against all rules.

        Args:
            charts: List of charts to check.

        Returns:
            List of all violations found across all charts.
        """
        return self.check_all_charts_with_progress(charts)

    def check_all_charts_with_progress(
        self,
        charts: list[ChartInfo],
        *,
        on_chart_done: Callable[[ChartInfo, list[ViolationResult], int, int], None]
        | None = None,
    ) -> list[ViolationResult]:
        """Check all charts and optionally emit per-chart completion progress.

        Args:
            charts: Charts to analyze.
            on_chart_done: Optional callback called after each chart completes.
                Callback arguments are `(chart, violations, completed, total)`.

        Returns:
            List of all violations found across all charts.
        """
        chart_count = len(charts)
        if chart_count == 0:
            return []

        worker_count = self._resolve_worker_count(chart_count)
        all_violations: list[ViolationResult] = []

        if worker_count == 1:
            for completed, chart in enumerate(charts, 1):
                violations = self.check_chart(chart)
                all_violations.extend(violations)
                if on_chart_done is not None:
                    on_chart_done(chart, violations, completed, chart_count)
            return all_violations

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_to_meta: dict[Future[list[ViolationResult]], tuple[int, ChartInfo]] = {
                executor.submit(self.check_chart, chart): (index, chart)
                for index, chart in enumerate(charts)
            }
            ordered_results: dict[int, list[ViolationResult]] = {}
            completed = 0
            for future in as_completed(future_to_meta):
                index, chart = future_to_meta[future]
                violations = future.result()
                ordered_results[index] = violations
                completed += 1
                if on_chart_done is not None:
                    on_chart_done(chart, violations, completed, chart_count)

            for index in range(chart_count):
                all_violations.extend(ordered_results.get(index, []))

        return all_violations

    def _resolve_worker_count(self, chart_count: int) -> int:
        """Resolve bounded worker count for parallel violation checks."""
        configured_workers = int(self.max_workers)
        if configured_workers > 0:
            return max(1, min(configured_workers, chart_count))
        cpu_count = os.cpu_count() or 4
        worker_cap = min(cpu_count, 10)
        mode = str(self.analysis_source or "auto").strip().lower()
        if mode in {"auto", "rendered"}:
            # Rendered checks spend most time in helm subprocesses, so using
            # small parallelism even for smaller chart sets improves throughput.
            return max(1, min(chart_count, max(2, worker_cap)))
        if chart_count < 8:
            return 1
        return max(1, min(chart_count, worker_cap))

    def generate_fix(
        self,
        chart: ChartInfo,
        violation: ViolationResult,
        ratio_strategy: str | None = None,
        ratio_target: str | None = None,
        probe_settings: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Generate a fix for a violation using FixGenerator.

        Args:
            chart: The ChartInfo containing the violation.
            violation: The violation to generate a fix for.
            ratio_strategy: Optional ratio strategy for RES005/RES006 fixes.
            ratio_target: Optional ratio fix target (`limit` or `request`).
            probe_settings: Optional probe override settings for PRB rules.

        Returns:
            Dictionary containing the fix details, or None if no fix available.
        """
        # Get the original rule violation for fix generation
        rule = get_rule_by_id(violation.id)
        if not rule:
            return None

        # Convert ChartInfo to dict for fix generation
        chart_dict = self._chart_info_to_dict(chart)

        # Create a mock violation in the format expected by FixGenerator
        rules_violation = RuleViolation(
            rule_id=violation.id,
            name=violation.rule_name,
            description=violation.description,
            severity=violation.severity.value,
            category="",
            fix_preview=None,
            auto_fixable=violation.fix_available,
        )

        fix_generator = FixGenerator()
        return fix_generator.generate_fix(
            rules_violation,
            chart_dict,
            ratio_strategy=ratio_strategy,
            ratio_target=ratio_target,
            probe_settings=probe_settings,
        )


# Backward compatibility alias
OptimizerController = UnifiedOptimizerController
