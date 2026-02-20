"""Unit tests for template patch suggester."""

from __future__ import annotations

from pathlib import Path

from kubeagle.optimizer.llm_patch_protocol import (
    parse_structured_patch_response,
)
from kubeagle.optimizer.template_patch_suggester import (
    build_template_patch_suggestions,
    format_wiring_suggestions_markdown,
)


def test_build_template_patch_suggestions_for_unmatched_keys() -> None:
    """Unmatched keys should produce missing-wiring reason and a rule snippet."""
    diagnosis = {
        "unmatched_keys": ["resources.requests.cpu"],
        "candidate_files": ["templates/deployment.yaml"],
    }

    suggestions = build_template_patch_suggestions(
        rule_id="RES002",
        diagnosis=diagnosis,
        fix_payload={"resources": {"requests": {"cpu": "100m"}}},
    )

    assert len(suggestions) == 1
    suggestion = suggestions[0]
    assert suggestion["file"] == "templates/deployment.yaml"
    assert "No .Values wiring found" in suggestion["reason"]
    assert ".Values.resources.requests.cpu" in suggestion["snippet"]
    assert suggestion["structured_patch_prompt"]
    parsed = parse_structured_patch_response(suggestion["structured_patch_response"])
    assert parsed.schema_version == "patch_response.v1"
    assert parsed.result in {"ok", "error"}


def test_format_wiring_suggestions_markdown() -> None:
    """Formatter should emit compact markdown with file/anchor/reason/snippet."""
    markdown = format_wiring_suggestions_markdown(
        [
            {
                "file": "templates/deployment.yaml",
                "anchor": "spec.template.spec.containers[0]",
                "reason": "Example reason",
                "snippet": "replicas: {{ .Values.replicaCount }}",
                "structured_patch_response": (
                    '{'
                    '"schema_version":"patch_response.v1",'
                    '"result":"ok",'
                    '"summary":"wired",'
                    '"patches":[{"file":"templates/deployment.yaml","purpose":"wire","unified_diff":"--- a/templates/deployment.yaml\\n+++ b/templates/deployment.yaml\\n@@ -1,1 +1,2 @@\\n+replicas: {{ .Values.replicaCount }}"}],'
                    '"warnings":[],"error":""'
                    '}'
                ),
            }
        ]
    )

    assert "**File:** `templates/deployment.yaml`" in markdown
    assert "**Anchor:** `spec.template.spec.containers[0]`" in markdown
    assert "Example reason" in markdown
    assert "replicas: {{ .Values.replicaCount }}" in markdown
    assert "### AI Patch Result" in markdown


def test_build_template_patch_suggestions_includes_patch_preview(tmp_path: Path) -> None:
    """Suggestion should include diff-style patch preview when file is discoverable."""
    chart_dir = tmp_path / "chart"
    templates = chart_dir / "templates"
    templates.mkdir(parents=True, exist_ok=True)
    (templates / "deployment.yaml").write_text(
        (
            "apiVersion: apps/v1\n"
            "kind: Deployment\n"
            "spec:\n"
            "  template:\n"
            "    spec:\n"
            "      containers:\n"
            "        - name: app\n"
            "          image: nginx\n"
        ),
        encoding="utf-8",
    )

    suggestions = build_template_patch_suggestions(
        rule_id="PRB001",
        diagnosis={"unmatched_keys": ["livenessProbe.httpGet.path"], "candidate_files": ["templates/deployment.yaml"]},
        fix_payload={"livenessProbe": {"httpGet": {"path": "/health", "port": "http"}}},
        chart_dir=chart_dir,
    )

    assert suggestions
    patch_preview = suggestions[0].get("patch_preview", "")
    assert patch_preview
    assert "--- a/templates/deployment.yaml" in patch_preview
    assert "+++ b/templates/deployment.yaml" in patch_preview
    assert "+          livenessProbe:" in patch_preview
    parsed = parse_structured_patch_response(suggestions[0]["structured_patch_response"])
    assert parsed.result == "ok"
    assert parsed.patches[0].file == "templates/deployment.yaml"


def test_probe_patch_preview_targets_containers_not_initcontainers(tmp_path: Path) -> None:
    """Probe patch preview should insert under containers block, not initContainers."""
    chart_dir = tmp_path / "chart"
    templates = chart_dir / "templates"
    templates.mkdir(parents=True, exist_ok=True)
    (templates / "deployment.yaml").write_text(
        (
            "apiVersion: apps/v1\n"
            "kind: Deployment\n"
            "spec:\n"
            "  template:\n"
            "    spec:\n"
            "      initContainers:\n"
            "        - name: init-db\n"
            "          image: busybox\n"
            "      containers:\n"
            "        - name: app\n"
            "          image: nginx\n"
        ),
        encoding="utf-8",
    )

    suggestions = build_template_patch_suggestions(
        rule_id="PRB003",
        diagnosis={"unmatched_keys": ["startupProbe.httpGet.path"], "candidate_files": ["templates/deployment.yaml"]},
        fix_payload={"startupProbe": {"httpGet": {"path": "/startup", "port": "http"}}},
        chart_dir=chart_dir,
    )

    assert suggestions
    patch_preview = suggestions[0].get("patch_preview", "")
    assert patch_preview
    assert "+          startupProbe:" in patch_preview
    assert "initContainers" not in patch_preview


def test_probe_structured_prompt_includes_container_scope_constraints() -> None:
    """Probe prompts should instruct models to avoid initContainers edits."""
    suggestions = build_template_patch_suggestions(
        rule_id="PRB003",
        diagnosis={"unmatched_keys": ["startupProbe.httpGet.path"], "candidate_files": ["templates/deployment.yaml"]},
        fix_payload={"startupProbe": {"httpGet": {"path": "/startup", "port": "http"}}},
    )

    prompt = suggestions[0]["structured_patch_prompt"]
    assert "spec.template.spec.containers[*]" in prompt
    assert "Do NOT add, edit, or move probes under `spec.template.spec.initContainers[*]`." in prompt


def test_format_wiring_suggestions_markdown_includes_patch_preview() -> None:
    """Markdown formatter should render a diff block when preview exists."""
    markdown = format_wiring_suggestions_markdown(
        [
            {
                "file": "templates/deployment.yaml",
                "anchor": "spec.template.spec.containers[0]",
                "reason": "Example reason",
                "snippet": "livenessProbe:\n{{- toYaml .Values.livenessProbe | nindent 2 }}",
                "patch_preview": "--- a/templates/deployment.yaml\n+++ b/templates/deployment.yaml\n@@ -1,1 +1,2 @@\n+livenessProbe:",
            }
        ]
    )

    assert "- **Patch Preview:**" in markdown
    assert "```diff" in markdown


def test_format_wiring_suggestions_markdown_falls_back_to_diff_on_invalid_contract() -> None:
    """Invalid structured payload should fall back to raw diff preview block."""
    markdown = format_wiring_suggestions_markdown(
        [
            {
                "file": "templates/deployment.yaml",
                "anchor": "spec.template.spec.containers[0]",
                "reason": "Example reason",
                "snippet": "livenessProbe:\n{{- toYaml .Values.livenessProbe | nindent 2 }}",
                "structured_patch_response": "not-json",
                "patch_preview": "--- a/templates/deployment.yaml\n+++ b/templates/deployment.yaml\n@@ -1,1 +1,2 @@\n+livenessProbe:",
            }
        ]
    )

    assert "- **Patch Preview:**" in markdown
    assert "```diff" in markdown
