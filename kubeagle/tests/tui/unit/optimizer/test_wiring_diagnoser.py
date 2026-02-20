"""Unit tests for template wiring diagnoser."""

from __future__ import annotations

from pathlib import Path

from kubeagle.optimizer.wiring_diagnoser import (
    diagnose_template_wiring,
    flatten_fix_paths,
)


def _create_chart_with_templates(tmp_path: Path) -> Path:
    chart_dir = tmp_path / "demo-chart"
    templates_dir = chart_dir / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (chart_dir / "Chart.yaml").write_text(
        "apiVersion: v2\nname: demo-chart\nversion: 0.1.0\n",
        encoding="utf-8",
    )
    (templates_dir / "deployment.yaml").write_text(
        (
            "resources:\n"
            "  requests:\n"
            "    cpu: {{ .Values.resources.requests.cpu | quote }}\n"
        ),
        encoding="utf-8",
    )
    return chart_dir


def test_flatten_fix_paths_maps_nested_payload() -> None:
    """Nested payload should be flattened to dot paths."""
    payload = {
        "resources": {"requests": {"cpu": "100m", "memory": "128Mi"}},
        "livenessProbe": {"httpGet": {"path": "/health", "port": "http"}},
    }

    paths = flatten_fix_paths(payload)

    assert "resources.requests.cpu" in paths
    assert "resources.requests.memory" in paths
    assert "livenessProbe.httpGet.path" in paths
    assert "livenessProbe.httpGet.port" in paths


def test_diagnose_template_wiring_reports_matches_and_unmatched_keys(tmp_path: Path) -> None:
    """Diagnosis should only report keys actually wired in templates."""
    chart_dir = _create_chart_with_templates(tmp_path)
    payload = {
        "resources": {"requests": {"cpu": "100m", "memory": "128Mi"}},
        "livenessProbe": {"httpGet": {"path": "/health"}},
    }

    diagnosis = diagnose_template_wiring(chart_dir=chart_dir, fix_payload=payload)

    assert diagnosis["templates_found"] is True
    assert "templates/deployment.yaml" in diagnosis["template_files"]
    assert diagnosis["key_matches"]["resources.requests.cpu"] == ["templates/deployment.yaml"]
    assert "resources.requests.memory" in diagnosis["unmatched_keys"]
    assert "livenessProbe.httpGet.path" in diagnosis["unmatched_keys"]
    assert diagnosis["candidate_files"][0] == "templates/deployment.yaml"


def test_diagnose_template_wiring_handles_missing_templates_dir(tmp_path: Path) -> None:
    """Missing templates directory should return unmatched payload keys."""
    chart_dir = tmp_path / "chart-without-templates"
    chart_dir.mkdir(parents=True, exist_ok=True)
    (chart_dir / "Chart.yaml").write_text(
        "apiVersion: v2\nname: chart-without-templates\nversion: 0.1.0\n",
        encoding="utf-8",
    )
    payload = {"replicaCount": 2}

    diagnosis = diagnose_template_wiring(chart_dir=chart_dir, fix_payload=payload)

    assert diagnosis["templates_found"] is False
    assert diagnosis["template_files"] == []
    assert diagnosis["unmatched_keys"] == ["replicaCount"]


def test_diagnose_template_wiring_prioritizes_workload_templates_over_helpers(
    tmp_path: Path,
) -> None:
    """Candidate discovery should prioritize real workload templates over helpers."""
    chart_dir = tmp_path / "demo-chart"
    templates_dir = chart_dir / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (chart_dir / "Chart.yaml").write_text(
        "apiVersion: v2\nname: demo-chart\nversion: 0.1.0\n",
        encoding="utf-8",
    )
    (templates_dir / "_helpers.tpl").write_text(
        "{{- define \"demo.topology\" -}}\n{{- toYaml .Values.topologySpreadConstraints -}}\n{{- end -}}\n",
        encoding="utf-8",
    )
    (templates_dir / "deployment.yaml").write_text(
        (
            "apiVersion: apps/v1\n"
            "kind: Deployment\n"
            "metadata:\n"
            "  name: demo\n"
            "spec:\n"
            "  template:\n"
            "    spec:\n"
            "      containers:\n"
            "        - name: app\n"
        ),
        encoding="utf-8",
    )
    payload = {"topologySpreadConstraints": [{"maxSkew": 1}]}

    diagnosis = diagnose_template_wiring(
        chart_dir=chart_dir,
        fix_payload=payload,
        rule_id="AVL004",
    )

    assert diagnosis["candidate_files"]
    assert diagnosis["candidate_files"][0] == "templates/deployment.yaml"
