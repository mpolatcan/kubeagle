"""Fix verification using rendered manifests as the source of truth."""

from __future__ import annotations

import copy
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from kubeagle.models.analysis.violation import ViolationResult
from kubeagle.models.charts.chart_info import ChartInfo
from kubeagle.optimizer.full_fix_applier import (
    apply_full_fix_bundle_atomic,
)
from kubeagle.optimizer.helm_renderer import HelmRenderResult, render_chart
from kubeagle.optimizer.llm_patch_protocol import FullFixTemplatePatch
from kubeagle.optimizer.rendered_rule_input import (
    build_rule_inputs_from_rendered,
)
from kubeagle.optimizer.rules import get_rule_by_id
from kubeagle.optimizer.template_patch_suggester import (
    build_template_patch_suggestions,
)
from kubeagle.optimizer.wiring_diagnoser import diagnose_template_wiring


@dataclass(slots=True)
class FixVerificationResult:
    """Verification state for a single violation fix action."""

    status: str  # verified|unresolved|unverified|not_run
    note: str = ""
    before_has_violation: bool | None = None
    after_has_violation: bool | None = None
    suggestions: list[dict[str, str]] = field(default_factory=list)


@dataclass(slots=True)
class FullFixBundleVerificationResult:
    """Verification state for chart-level full fix bundle."""

    status: str  # verified|unresolved|unverified|not_run
    note: str = ""
    per_violation: dict[str, FixVerificationResult] = field(default_factory=dict)


def verify_fix_preview(
    *,
    chart: ChartInfo,
    violation: ViolationResult,
    fix_payload: dict[str, Any],
    timeout_seconds: int = 30,
) -> FixVerificationResult:
    """Check whether fix would resolve violation before applying."""
    local_paths = _resolve_local_paths(chart)
    if local_paths is None:
        return FixVerificationResult(
            status="not_run",
            note="Verification skipped: chart values file is not a local path.",
        )
    chart_dir, values_path = local_paths

    current_values = _read_values_as_mapping(values_path)
    if current_values is None:
        return FixVerificationResult(
            status="unverified",
            note=f"Verification failed: unable to parse values file `{values_path}`.",
        )

    proposed_values = _deep_merge(copy.deepcopy(current_values), fix_payload)
    try:
        proposed_values_content = yaml.dump(
            proposed_values,
            default_flow_style=False,
            sort_keys=False,
        )
    except Exception as exc:
        return FixVerificationResult(
            status="unverified",
            note=f"Verification failed: could not serialize proposed values ({exc!s}).",
        )

    current_render = render_chart(
        chart_dir=chart_dir,
        values_file=values_path,
        release_name=chart.name,
        timeout_seconds=timeout_seconds,
    )
    if not current_render.ok:
        return _unverified_from_render_result(current_render, "current values")

    proposed_render = render_chart(
        chart_dir=chart_dir,
        values_file=values_path,
        values_content=proposed_values_content,
        release_name=chart.name,
        timeout_seconds=timeout_seconds,
    )
    if not proposed_render.ok:
        return _unverified_from_render_result(proposed_render, "proposed values")

    before_has, after_has = _evaluate_rule_from_render(
        violation=violation,
        chart_name=chart.name,
        before_render=current_render,
        after_render=proposed_render,
    )
    if before_has is None or after_has is None:
        return FixVerificationResult(
            status="unverified",
            note="Verification failed: rule could not be evaluated on rendered manifests.",
        )
    if not after_has:
        return FixVerificationResult(
            status="verified",
            note="Rendered verification passed: violation is resolved by proposed fix.",
            before_has_violation=before_has,
            after_has_violation=after_has,
        )

    diagnosis = diagnose_template_wiring(
        chart_dir=chart_dir,
        fix_payload=fix_payload,
        rule_id=violation.rule_id,
    )
    suggestions = build_template_patch_suggestions(
        rule_id=violation.rule_id,
        diagnosis=diagnosis,
        fix_payload=fix_payload,
        chart_dir=chart_dir,
    )
    return FixVerificationResult(
        status="unresolved",
        note="Rendered verification failed: violation still exists after applying proposed values.",
        before_has_violation=before_has,
        after_has_violation=after_has,
        suggestions=suggestions,
    )


def verify_fix_after_apply(
    *,
    chart: ChartInfo,
    violation: ViolationResult,
    fix_payload: dict[str, Any],
    timeout_seconds: int = 30,
) -> FixVerificationResult:
    """Verify applied fix by checking current rendered output."""
    local_paths = _resolve_local_paths(chart)
    if local_paths is None:
        return FixVerificationResult(
            status="not_run",
            note="Verification skipped: chart values file is not a local path.",
        )
    chart_dir, values_path = local_paths
    current_render = render_chart(
        chart_dir=chart_dir,
        values_file=values_path,
        release_name=chart.name,
        timeout_seconds=timeout_seconds,
    )
    if not current_render.ok:
        return _unverified_from_render_result(current_render, "applied values")

    inputs = build_rule_inputs_from_rendered(current_render.docs, chart_name=chart.name)
    has_violation = _rule_matches(violation.rule_id, inputs)
    if has_violation is None:
        return FixVerificationResult(
            status="unverified",
            note="Verification failed: rule evaluation failed on applied manifests.",
        )
    if not has_violation:
        return FixVerificationResult(
            status="verified",
            note="Rendered verification passed after apply.",
            after_has_violation=False,
        )

    diagnosis = diagnose_template_wiring(
        chart_dir=chart_dir,
        fix_payload=fix_payload,
        rule_id=violation.rule_id,
    )
    suggestions = build_template_patch_suggestions(
        rule_id=violation.rule_id,
        diagnosis=diagnosis,
        fix_payload=fix_payload,
        chart_dir=chart_dir,
    )
    return FixVerificationResult(
        status="unresolved",
        note="Rendered verification failed after apply: violation still exists.",
        after_has_violation=True,
        suggestions=suggestions,
    )


def verify_full_fix_bundle_preview(
    *,
    chart: ChartInfo,
    violations: list[ViolationResult],
    values_patch: dict[str, Any],
    template_patches: list[FullFixTemplatePatch],
    timeout_seconds: int = 30,
) -> FullFixBundleVerificationResult:
    """Verify full-fix bundle by staging chart copy and evaluating all violations."""
    local_paths = _resolve_local_paths(chart)
    if local_paths is None:
        return FullFixBundleVerificationResult(
            status="not_run",
            note="Verification skipped: chart values file is not a local path.",
        )
    chart_dir, values_path = local_paths

    with tempfile.TemporaryDirectory(prefix="kubeagle-full-fix-") as tmp_dir:
        staged_chart_dir = Path(tmp_dir) / chart_dir.name
        try:
            shutil.copytree(chart_dir, staged_chart_dir)
        except OSError as exc:
            return FullFixBundleVerificationResult(
                status="unverified",
                note=f"Verification failed: unable to stage chart copy ({exc!s}).",
            )

        try:
            rel_values = values_path.relative_to(chart_dir)
        except ValueError:
            rel_values = Path(values_path.name)
        staged_values_path = staged_chart_dir / rel_values
        if not staged_values_path.exists():
            staged_values_path = staged_chart_dir / values_path.name
            if not staged_values_path.exists():
                return FullFixBundleVerificationResult(
                    status="unverified",
                    note="Verification failed: staged values file path could not be resolved.",
                )

        apply_result = apply_full_fix_bundle_atomic(
            chart_dir=staged_chart_dir,
            values_path=staged_values_path,
            values_patch=values_patch,
            template_patches=template_patches,
        )
        if not apply_result.ok:
            return FullFixBundleVerificationResult(
                status="unverified",
                note=f"Verification failed while staging bundle: {apply_result.note}",
            )

        render_result = render_chart(
            chart_dir=staged_chart_dir,
            values_file=staged_values_path,
            release_name=chart.name,
            timeout_seconds=timeout_seconds,
        )
        if not render_result.ok:
            partial = _unverified_from_render_result(render_result, "staged full-fix values")
            return FullFixBundleVerificationResult(
                status="unverified",
                note=partial.note,
            )

        inputs = build_rule_inputs_from_rendered(render_result.docs, chart_name=chart.name)
        return _evaluate_bundle_violation_results(
            violations=violations,
            inputs=inputs,
            unresolved_note="Violation still exists after applying chart-level full fix bundle.",
            resolved_note="Violation resolved by chart-level full fix bundle.",
            unverified_note="Rule evaluation failed on rendered staged manifests.",
        )


def verify_full_fix_bundle_staged(
    *,
    chart: ChartInfo,
    violations: list[ViolationResult],
    staged_chart_dir: Path,
    rel_values_path: str,
    timeout_seconds: int = 30,
) -> FullFixBundleVerificationResult:
    """Verify already-staged chart workspace without re-applying patches."""
    staged_chart_dir = staged_chart_dir.expanduser().resolve()
    staged_values_path = (staged_chart_dir / rel_values_path).resolve()
    if not str(staged_values_path).startswith(str(staged_chart_dir)) or not staged_values_path.exists():
        return FullFixBundleVerificationResult(
            status="unverified",
            note="Verification failed: staged values file path could not be resolved.",
        )
    render_result = render_chart(
        chart_dir=staged_chart_dir,
        values_file=staged_values_path,
        release_name=chart.name,
        timeout_seconds=timeout_seconds,
    )
    if not render_result.ok:
        partial = _unverified_from_render_result(render_result, "staged full-fix values")
        return FullFixBundleVerificationResult(
            status="unverified",
            note=partial.note,
        )
    inputs = build_rule_inputs_from_rendered(render_result.docs, chart_name=chart.name)
    return _evaluate_bundle_violation_results(
        violations=violations,
        inputs=inputs,
        unresolved_note="Violation still exists after applying staged full-fix workspace.",
        resolved_note="Violation resolved by staged full-fix workspace.",
        unverified_note="Rule evaluation failed on rendered staged manifests.",
    )


def _resolve_local_paths(chart: ChartInfo) -> tuple[Path, Path] | None:
    values_file = str(chart.values_file or "")
    if not values_file or values_file.startswith("cluster:"):
        return None
    values_path = Path(values_file).expanduser().resolve()
    if not values_path.exists():
        return None
    chart_dir = values_path.parent
    if not (chart_dir / "Chart.yaml").exists():
        return None
    return chart_dir, values_path


def _read_values_as_mapping(values_path: Path) -> dict[str, Any] | None:
    try:
        raw = values_path.read_text(encoding="utf-8")
        parsed = yaml.safe_load(raw) or {}
    except (OSError, yaml.YAMLError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            nested_base = base[key]
            nested_override = value
            if isinstance(nested_base, dict) and isinstance(nested_override, dict):
                _deep_merge(nested_base, nested_override)
            else:
                base[key] = copy.deepcopy(value)
        else:
            base[key] = copy.deepcopy(value)
    return base


def _evaluate_rule_from_render(
    *,
    violation: ViolationResult,
    chart_name: str,
    before_render: HelmRenderResult,
    after_render: HelmRenderResult,
) -> tuple[bool | None, bool | None]:
    before_inputs = build_rule_inputs_from_rendered(before_render.docs, chart_name=chart_name)
    after_inputs = build_rule_inputs_from_rendered(after_render.docs, chart_name=chart_name)
    before_has = _rule_matches(violation.rule_id, before_inputs)
    after_has = _rule_matches(violation.rule_id, after_inputs)
    return before_has, after_has


def _rule_matches(rule_id: str, inputs: list[dict[str, Any]]) -> bool | None:
    rule = get_rule_by_id(rule_id)
    if rule is None:
        return None
    if not inputs:
        return False
    try:
        return any(bool(rule.check(item)) for item in inputs)
    except Exception:
        return None


def _unverified_from_render_result(
    render_result: HelmRenderResult,
    source_label: str,
) -> FixVerificationResult:
    error_parts = []
    if render_result.error_kind:
        error_parts.append(render_result.error_kind)
    if render_result.error_message:
        error_parts.append(render_result.error_message)
    elif render_result.stderr:
        error_parts.append(render_result.stderr.strip())
    error_text = " | ".join(part for part in error_parts if part)
    if not error_text:
        error_text = "unknown render error"
    dependency_hint = ""
    if (
        render_result.error_kind in {"parent_render_failed", "parent_render_setup_failed"}
        or "missing in charts/" in error_text.lower()
    ):
        dependency_hint = (
            " Parent-chart-only verification mode could not render this chart."
        )
    return FixVerificationResult(
        status="unverified",
        note=(
            f"Verification failed while rendering {source_label}: "
            f"{error_text}{dependency_hint}"
        ),
    )


def _evaluate_bundle_violation_results(
    *,
    violations: list[ViolationResult],
    inputs: list[dict[str, Any]],
    unresolved_note: str,
    resolved_note: str,
    unverified_note: str,
) -> FullFixBundleVerificationResult:
    per_violation: dict[str, FixVerificationResult] = {}
    counts = {"verified": 0, "unresolved": 0, "unverified": 0}
    for violation in violations:
        has_violation = _rule_matches(violation.rule_id, inputs)
        if has_violation is None:
            result = FixVerificationResult(
                status="unverified",
                note=unverified_note,
            )
            counts["unverified"] += 1
        elif has_violation:
            result = FixVerificationResult(
                status="unresolved",
                note=unresolved_note,
                after_has_violation=True,
            )
            counts["unresolved"] += 1
        else:
            result = FixVerificationResult(
                status="verified",
                note=resolved_note,
                after_has_violation=False,
            )
            counts["verified"] += 1
        per_violation[_violation_identity_key(violation)] = result

    aggregate_status = "verified"
    if counts["unverified"] > 0:
        aggregate_status = "unverified"
    elif counts["unresolved"] > 0:
        aggregate_status = "unresolved"
    note = (
        f"Bundle verification: {counts['verified']} verified, "
        f"{counts['unresolved']} unresolved, "
        f"{counts['unverified']} unverified."
    )
    return FullFixBundleVerificationResult(
        status=aggregate_status,
        note=note,
        per_violation=per_violation,
    )


def _violation_identity_key(violation: ViolationResult) -> str:
    """Stable key for chart-level per-violation verification mapping."""
    return (
        f"{violation.chart_name}|{violation.rule_id}|"
        f"{violation.rule_name}|{violation.current_value}"
    )
