"""Unit tests for template patch suggester."""

from __future__ import annotations

from kubeagle.optimizer.template_patch_suggester import (
    format_wiring_suggestions_markdown,
)


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
