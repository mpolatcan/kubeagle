"""Unit tests for rendered fix verifier outcomes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from kubeagle.constants.enums import QoSClass, Severity
from kubeagle.models.analysis.violation import ViolationResult
from kubeagle.models.charts.chart_info import ChartInfo
from kubeagle.optimizer import fix_verifier
from kubeagle.optimizer.full_fix_applier import FullFixApplyResult
from kubeagle.optimizer.helm_renderer import HelmRenderResult
from kubeagle.optimizer.llm_patch_protocol import FullFixTemplatePatch


def _create_local_chart(tmp_path: Path, *, values_file: str | None = None) -> ChartInfo:
    chart_dir = tmp_path / "payments"
    chart_dir.mkdir(parents=True, exist_ok=True)
    (chart_dir / "Chart.yaml").write_text(
        "apiVersion: v2\nname: payments\nversion: 0.1.0\n",
        encoding="utf-8",
    )
    local_values = chart_dir / "values.yaml"
    local_values.write_text("replicaCount: 2\n", encoding="utf-8")

    return ChartInfo(
        name="payments",
        team="payments",
        values_file=values_file or str(local_values),
        namespace="default",
        cpu_request=100.0,
        cpu_limit=200.0,
        memory_request=128 * 1024 * 1024,
        memory_limit=256 * 1024 * 1024,
        qos_class=QoSClass.BURSTABLE,
        has_liveness=False,
        has_readiness=True,
        has_startup=False,
        has_anti_affinity=False,
        has_topology_spread=False,
        has_topology=False,
        pdb_enabled=False,
        pdb_template_exists=False,
        pdb_min_available=None,
        pdb_max_unavailable=None,
        replicas=2,
        priority_class=None,
    )


def _violation(rule_id: str = "PRB001") -> ViolationResult:
    return ViolationResult(
        id=rule_id,
        chart_name="payments",
        rule_name="Missing Liveness Probe",
        rule_id=rule_id,
        category="probes",
        severity=Severity.WARNING,
        description="Container has no liveness probe",
        current_value="Not configured",
        recommended_value="Add livenessProbe",
        fix_available=True,
    )


def _deployment_doc(*, with_liveness: bool) -> dict[str, Any]:
    container: dict[str, Any] = {
        "name": "app",
        "resources": {
            "requests": {"cpu": "100m", "memory": "128Mi"},
            "limits": {"cpu": "200m", "memory": "256Mi"},
        },
    }
    if with_liveness:
        container["livenessProbe"] = {"httpGet": {"path": "/health", "port": "http"}}
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": "payments"},
        "spec": {
            "replicas": 2,
            "template": {
                "spec": {
                    "containers": [container],
                }
            },
        },
    }


def _render_ok(chart: ChartInfo, docs: list[dict[str, Any]]) -> HelmRenderResult:
    values_path = Path(chart.values_file if not chart.values_file.startswith("cluster:") else "/tmp")
    return HelmRenderResult(
        ok=True,
        chart_dir=values_path.parent,
        values_file=values_path,
        docs=docs,
    )


def test_verify_fix_preview_returns_verified(monkeypatch, tmp_path: Path) -> None:
    """Preview verification should pass when rendered rule is resolved."""
    chart = _create_local_chart(tmp_path)
    violation = _violation("PRB001")
    results = [
        _render_ok(chart, [_deployment_doc(with_liveness=False)]),
        _render_ok(chart, [_deployment_doc(with_liveness=True)]),
    ]

    monkeypatch.setattr(fix_verifier, "render_chart", lambda **kwargs: results.pop(0))

    result = fix_verifier.verify_fix_preview(
        chart=chart,
        violation=violation,
        fix_payload={"livenessProbe": {"httpGet": {"path": "/health", "port": "http"}}},
    )

    assert result.status == "verified"
    assert result.before_has_violation is True
    assert result.after_has_violation is False


def test_verify_fix_preview_returns_unresolved(monkeypatch, tmp_path: Path) -> None:
    """Preview verification should mark unresolved when violation persists."""
    chart = _create_local_chart(tmp_path)
    violation = _violation("PRB001")
    results = [
        _render_ok(chart, [_deployment_doc(with_liveness=False)]),
        _render_ok(chart, [_deployment_doc(with_liveness=False)]),
    ]

    monkeypatch.setattr(fix_verifier, "render_chart", lambda **kwargs: results.pop(0))
    monkeypatch.setattr(
        fix_verifier,
        "diagnose_template_wiring",
        lambda **kwargs: {
            "unmatched_keys": ["livenessProbe.httpGet.path"],
            "candidate_files": ["templates/deployment.yaml"],
        },
    )
    monkeypatch.setattr(
        fix_verifier,
        "build_template_patch_suggestions",
        lambda **kwargs: [
            {
                "file": "templates/deployment.yaml",
                "anchor": "spec.template.spec.containers[0]",
                "reason": "missing wiring",
                "snippet": "livenessProbe:\n{{- toYaml .Values.livenessProbe | nindent 2 }}",
            }
        ],
    )

    result = fix_verifier.verify_fix_preview(
        chart=chart,
        violation=violation,
        fix_payload={"livenessProbe": {"httpGet": {"path": "/health"}}},
    )

    assert result.status == "unresolved"
    assert result.after_has_violation is True
    assert len(result.suggestions) == 1


def test_verify_fix_preview_returns_unverified_on_render_error(monkeypatch, tmp_path: Path) -> None:
    """Preview verification should mark unverified when helm render fails."""
    chart = _create_local_chart(tmp_path)
    violation = _violation("PRB001")
    values_path = Path(chart.values_file)

    monkeypatch.setattr(
        fix_verifier,
        "render_chart",
        lambda **kwargs: HelmRenderResult(
            ok=False,
            chart_dir=values_path.parent,
            values_file=values_path,
            error_kind="helm_missing",
            error_message="helm binary not found",
        ),
    )

    result = fix_verifier.verify_fix_preview(
        chart=chart,
        violation=violation,
        fix_payload={"livenessProbe": {"httpGet": {"path": "/health"}}},
    )

    assert result.status == "unverified"
    assert "helm_missing" in result.note


def test_verify_fix_preview_skips_cluster_values(tmp_path: Path) -> None:
    """Cluster-backed values should skip template verification."""
    chart = _create_local_chart(tmp_path, values_file="cluster:payments")
    violation = _violation("PRB001")

    result = fix_verifier.verify_fix_preview(
        chart=chart,
        violation=violation,
        fix_payload={"livenessProbe": {"httpGet": {"path": "/health"}}},
    )

    assert result.status == "not_run"


def test_verify_fix_after_apply_verified(monkeypatch, tmp_path: Path) -> None:
    """Post-apply verification should pass when rendered violation is gone."""
    chart = _create_local_chart(tmp_path)
    violation = _violation("PRB001")
    monkeypatch.setattr(
        fix_verifier,
        "render_chart",
        lambda **kwargs: _render_ok(chart, [_deployment_doc(with_liveness=True)]),
    )

    result = fix_verifier.verify_fix_after_apply(
        chart=chart,
        violation=violation,
        fix_payload={"livenessProbe": {"httpGet": {"path": "/health"}}},
    )

    assert result.status == "verified"
    assert result.after_has_violation is False


def test_verify_fix_after_apply_unresolved(monkeypatch, tmp_path: Path) -> None:
    """Post-apply verification should include suggestions when violation remains."""
    chart = _create_local_chart(tmp_path)
    violation = _violation("PRB001")
    monkeypatch.setattr(
        fix_verifier,
        "render_chart",
        lambda **kwargs: _render_ok(chart, [_deployment_doc(with_liveness=False)]),
    )
    monkeypatch.setattr(
        fix_verifier,
        "diagnose_template_wiring",
        lambda **kwargs: {
            "unmatched_keys": ["livenessProbe.httpGet.path"],
            "candidate_files": ["templates/deployment.yaml"],
        },
    )
    monkeypatch.setattr(
        fix_verifier,
        "build_template_patch_suggestions",
        lambda **kwargs: [
            {
                "file": "templates/deployment.yaml",
                "anchor": "spec.template.spec.containers[0]",
                "reason": "missing wiring",
                "snippet": "livenessProbe:\n{{- toYaml .Values.livenessProbe | nindent 2 }}",
            }
        ],
    )

    result = fix_verifier.verify_fix_after_apply(
        chart=chart,
        violation=violation,
        fix_payload={"livenessProbe": {"httpGet": {"path": "/health"}}},
    )

    assert result.status == "unresolved"
    assert result.after_has_violation is True
    assert len(result.suggestions) == 1


def test_verify_fix_after_apply_unverified_on_render_error(monkeypatch, tmp_path: Path) -> None:
    """Post-apply verification should mark unverified on render failure."""
    chart = _create_local_chart(tmp_path)
    violation = _violation("PRB001")
    values_path = Path(chart.values_file)

    monkeypatch.setattr(
        fix_verifier,
        "render_chart",
        lambda **kwargs: HelmRenderResult(
            ok=False,
            chart_dir=values_path.parent,
            values_file=values_path,
            error_kind="render_failed",
            error_message="template failed",
        ),
    )

    result = fix_verifier.verify_fix_after_apply(
        chart=chart,
        violation=violation,
        fix_payload={"livenessProbe": {"httpGet": {"path": "/health"}}},
    )

    assert result.status == "unverified"
    assert "render_failed" in result.note


def test_verify_fix_preview_dependency_error_includes_hint(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Dependency build failures should include non-manual remediation hint."""
    chart = _create_local_chart(tmp_path)
    violation = _violation("PRB001")
    values_path = Path(chart.values_file)

    monkeypatch.setattr(
        fix_verifier,
        "render_chart",
        lambda **kwargs: HelmRenderResult(
            ok=False,
            chart_dir=values_path.parent,
            values_file=values_path,
            error_kind="parent_render_failed",
            error_message="missing dependency: parameter-store",
            parent_only_render_attempted=True,
        ),
    )

    result = fix_verifier.verify_fix_preview(
        chart=chart,
        violation=violation,
        fix_payload={"livenessProbe": {"httpGet": {"path": "/health"}}},
    )

    assert result.status == "unverified"
    assert "Parent-chart-only verification mode" in result.note


def test_verify_full_fix_bundle_preview_verified(monkeypatch, tmp_path: Path) -> None:
    """Chart-level full-fix preview should verify all included violations."""
    chart = _create_local_chart(tmp_path)
    violations = [_violation("PRB001")]

    monkeypatch.setattr(
        fix_verifier,
        "apply_full_fix_bundle_atomic",
        lambda **kwargs: FullFixApplyResult(ok=True, status="ok"),
    )
    monkeypatch.setattr(
        fix_verifier,
        "render_chart",
        lambda **kwargs: _render_ok(chart, [_deployment_doc(with_liveness=True)]),
    )

    result = fix_verifier.verify_full_fix_bundle_preview(
        chart=chart,
        violations=violations,
        values_patch={"livenessProbe": {"httpGet": {"path": "/health"}}},
        template_patches=[
            FullFixTemplatePatch(
                file="templates/deployment.yaml",
                purpose="wire probe",
                unified_diff="--- a/templates/deployment.yaml\n+++ b/templates/deployment.yaml\n@@ -1,1 +1,2 @@\n+probe",
            )
        ],
    )

    assert result.status == "verified"
    assert result.per_violation
    assert list(result.per_violation.values())[0].status == "verified"


def test_verify_full_fix_bundle_preview_unverified_on_apply_failure(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Chart-level bundle verification should fail when staged apply fails."""
    chart = _create_local_chart(tmp_path)
    violations = [_violation("PRB001")]

    monkeypatch.setattr(
        fix_verifier,
        "apply_full_fix_bundle_atomic",
        lambda **kwargs: FullFixApplyResult(
            ok=False,
            status="error",
            note="diff parse failed",
        ),
    )

    result = fix_verifier.verify_full_fix_bundle_preview(
        chart=chart,
        violations=violations,
        values_patch={},
        template_patches=[],
    )

    assert result.status == "unverified"
    assert "diff parse failed" in result.note


def test_verify_full_fix_bundle_staged_verified(monkeypatch, tmp_path: Path) -> None:
    """Staged verification should evaluate violations directly from staged chart."""
    chart = _create_local_chart(tmp_path)
    violations = [_violation("PRB001")]
    staged_chart = tmp_path / "staged" / "payments"
    staged_chart.mkdir(parents=True)
    (staged_chart / "Chart.yaml").write_text(
        "apiVersion: v2\nname: payments\nversion: 0.1.0\n",
        encoding="utf-8",
    )
    (staged_chart / "values.yaml").write_text("replicaCount: 2\n", encoding="utf-8")

    monkeypatch.setattr(
        fix_verifier,
        "render_chart",
        lambda **kwargs: _render_ok(chart, [_deployment_doc(with_liveness=True)]),
    )

    result = fix_verifier.verify_full_fix_bundle_staged(
        chart=chart,
        violations=violations,
        staged_chart_dir=staged_chart,
        rel_values_path="values.yaml",
    )

    assert result.status == "verified"
    assert result.per_violation
    assert list(result.per_violation.values())[0].status == "verified"


def test_verify_full_fix_bundle_staged_unverified_when_values_missing(tmp_path: Path) -> None:
    """Staged verification should fail early when staged values file is missing."""
    chart = _create_local_chart(tmp_path)
    staged_chart = tmp_path / "staged" / "payments"
    staged_chart.mkdir(parents=True)
    (staged_chart / "Chart.yaml").write_text(
        "apiVersion: v2\nname: payments\nversion: 0.1.0\n",
        encoding="utf-8",
    )

    result = fix_verifier.verify_full_fix_bundle_staged(
        chart=chart,
        violations=[_violation("PRB001")],
        staged_chart_dir=staged_chart,
        rel_values_path="values.yaml",
    )

    assert result.status == "unverified"
    assert "staged values file" in result.note.lower()
