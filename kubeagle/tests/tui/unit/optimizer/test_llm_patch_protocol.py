"""Unit tests for structured LLM patch contract module."""

from __future__ import annotations

import pytest

from kubeagle.optimizer.llm_patch_protocol import (
    build_full_fix_prompt,
    build_structured_patch_prompt,
    format_full_fix_preview_markdown,
    format_structured_patch_preview_markdown,
    parse_full_fix_response,
    parse_structured_patch_response,
    with_system_prompt_override,
)


def test_build_structured_patch_prompt_contains_allowlist_and_contract() -> None:
    """Prompt should include strict contract instructions and allowed files."""
    prompt = build_structured_patch_prompt(
        task="Add liveness probe wiring.",
        allowed_files=["templates/deployment.yaml", "templates/statefulset.yaml"],
        context_blocks=[
            ("Violation", "Rule: PRB001"),
            ("Suggested Keys", "livenessProbe.httpGet.path"),
        ],
    )

    assert "Return output as a single JSON object only." in prompt
    assert "schema_version" in prompt
    assert "- templates/deployment.yaml" in prompt
    assert "- templates/statefulset.yaml" in prompt
    assert "## Violation" in prompt


def test_build_structured_patch_prompt_applies_system_override() -> None:
    """Structured prompt should prepend configured system override text."""
    prompt = build_structured_patch_prompt(
        task="Add liveness probe wiring.",
        allowed_files=["templates/deployment.yaml"],
        system_prompt_override="Always preserve existing helper includes.",
    )

    assert "Additional system instructions (configured override):" in prompt
    assert "Always preserve existing helper includes." in prompt


def test_parse_structured_patch_response_accepts_plain_json() -> None:
    """Parser should accept direct JSON object output."""
    raw = (
        '{'
        '"schema_version":"patch_response.v1",'
        '"result":"ok",'
        '"summary":"wired liveness",'
        '"patches":[{"file":"templates/deployment.yaml","purpose":"add probe","unified_diff":"--- a/templates/deployment.yaml\\n+++ b/templates/deployment.yaml\\n@@ -1,1 +1,2 @@\\n+livenessProbe:"}],'
        '"warnings":[],"error":""'
        '}'
    )

    parsed = parse_structured_patch_response(raw)

    assert parsed.result == "ok"
    assert len(parsed.patches) == 1
    assert parsed.patches[0].file == "templates/deployment.yaml"


def test_parse_structured_patch_response_accepts_fenced_json() -> None:
    """Parser should recover JSON from markdown fence if provider wraps output."""
    raw = (
        "```json\n"
        '{'
        '"schema_version":"patch_response.v1",'
        '"result":"no_change",'
        '"summary":"already wired",'
        '"patches":[],"warnings":["none"],"error":""'
        "}\n"
        "```"
    )

    parsed = parse_structured_patch_response(raw)

    assert parsed.result == "no_change"
    assert parsed.warnings == ["none"]


def test_parse_structured_patch_response_accepts_wrapped_json_with_prose() -> None:
    """Parser should recover object JSON when provider adds prose around output."""
    raw = (
        "Here is the result:\n"
        '{'
        '"schema_version":"patch_response.v1",'
        '"result":"ok",'
        '"summary":"wrapped",'
        '"patches":[{"file":"templates/deployment.yaml","purpose":"wire","unified_diff":"--- a/templates/deployment.yaml\\n+++ b/templates/deployment.yaml"}],'
        '"warnings":[],"error":""'
        "}\n"
        "Thanks."
    )
    parsed = parse_structured_patch_response(raw)
    assert parsed.result == "ok"
    assert parsed.summary == "wrapped"


def test_parse_structured_patch_response_uses_first_schema_valid_object() -> None:
    """Parser should skip unrelated JSON object and parse contract-compatible object."""
    raw = (
        '{"meta":"diagnostics"}\n'
        '{'
        '"schema_version":"patch_response.v1",'
        '"result":"ok",'
        '"summary":"valid object",'
        '"patches":[{"file":"templates/deployment.yaml","purpose":"wire","unified_diff":"--- a/templates/deployment.yaml\\n+++ b/templates/deployment.yaml"}],'
        '"warnings":[],"error":""'
        "}"
    )
    parsed = parse_structured_patch_response(raw)
    assert parsed.result == "ok"
    assert parsed.summary == "valid object"


def test_parse_structured_patch_response_rejects_invalid_payload() -> None:
    """Parser should fail on non-contract outputs."""
    with pytest.raises(ValueError):
        parse_structured_patch_response("not-json")


def test_format_structured_patch_preview_markdown() -> None:
    """Formatter should produce dialog-friendly diff preview."""
    parsed = parse_structured_patch_response(
        '{'
        '"schema_version":"patch_response.v1",'
        '"result":"ok",'
        '"summary":"added wiring",'
        '"patches":[{"file":"templates/deployment.yaml","purpose":"wire values","unified_diff":"--- a/templates/deployment.yaml\\n+++ b/templates/deployment.yaml\\n@@ -1,1 +1,2 @@\\n+livenessProbe:"}],'
        '"warnings":["check indent"],"error":""'
        '}'
    )

    markdown = format_structured_patch_preview_markdown(parsed)

    assert "### AI Patch Result" in markdown
    assert "**Result:** `OK`" in markdown
    assert "```diff" in markdown
    assert "livenessProbe" in markdown


def test_build_full_fix_prompt_contains_contract_and_allowlist() -> None:
    """Full-fix prompt should include strict schema and allowed template files."""
    prompt = build_full_fix_prompt(
        task="Fix PRB001 and RES005 for chart.",
        allowed_files=["templates/deployment.yaml", "templates/_helpers.tpl"],
        context_blocks=[("Violation", "PRB001, RES005")],
    )
    assert "full_fix_response.v1" in prompt
    assert "values_patch" in prompt
    assert "template_patches" in prompt
    assert "- templates/deployment.yaml" in prompt
    assert "Return output as a single JSON object only." in prompt
    assert "Always provide `template_patches[].updated_content`" in prompt
    assert "Do not invent alias or suffixed keys" in prompt
    assert "resourcesAutomation" in prompt


def test_build_full_fix_prompt_applies_system_override() -> None:
    """Full-fix prompt should prepend configured system override text."""
    prompt = build_full_fix_prompt(
        task="Fix PRB001 and RES005 for chart.",
        allowed_files=["templates/deployment.yaml"],
        system_prompt_override="Never touch helper templates.",
    )
    assert "Additional system instructions (configured override):" in prompt
    assert "Never touch helper templates." in prompt


def test_with_system_prompt_override_returns_base_when_override_empty() -> None:
    """Helper should keep original prompt unchanged when override is empty."""
    base_prompt = "Return JSON only."
    assert with_system_prompt_override(base_prompt, system_prompt_override="") == base_prompt


def test_parse_full_fix_response_accepts_plain_json() -> None:
    """Full-fix parser should accept valid JSON payload."""
    raw = (
        "{"
        '"schema_version":"full_fix_response.v1",'
        '"result":"ok",'
        '"summary":"chart fixed",'
        '"values_patch":{"replicaCount":2},'
        '"template_patches":[{"file":"templates/deployment.yaml","purpose":"wire probe","unified_diff":"--- a/templates/deployment.yaml\\n+++ b/templates/deployment.yaml\\n@@ -1,1 +1,2 @@\\n+startupProbe:"}],'
        '"violation_coverage":[{"rule_id":"PRB003","status":"addressed","note":"added startup probe"}],'
        '"warnings":[],"error":""'
        "}"
    )
    parsed = parse_full_fix_response(raw)
    assert parsed.result == "ok"
    assert parsed.values_patch["replicaCount"] == 2
    assert len(parsed.template_patches) == 1
    assert parsed.violation_coverage[0].rule_id == "PRB003"


def test_parse_full_fix_response_accepts_fenced_nested_json() -> None:
    """Parser should recover full nested JSON object from fenced payload."""
    raw = (
        "```json\n"
        "{\n"
        '  "schema_version":"full_fix_response.v1",\n'
        '  "result":"ok",\n'
        '  "summary":"nested fenced",\n'
        '  "values_patch":{"resources":{"requests":{"cpu":"100m"}}},\n'
        '  "template_patches":[{"file":"templates/deployment.yaml","purpose":"wire","unified_diff":"--- a/templates/deployment.yaml\\n+++ b/templates/deployment.yaml"}],\n'
        '  "violation_coverage":[{"rule_id":"RES005","status":"addressed","note":"updated"}],\n'
        '  "warnings":[],\n'
        '  "error":""\n'
        "}\n"
        "```"
    )
    parsed = parse_full_fix_response(raw)
    assert parsed.result == "ok"
    assert parsed.values_patch["resources"]["requests"]["cpu"] == "100m"


def test_parse_full_fix_response_uses_first_schema_valid_object() -> None:
    """Full-fix parser should skip unrelated JSON and parse first valid schema payload."""
    raw = (
        '{"trace_id":"abc123"}\n'
        "{"
        '"schema_version":"full_fix_response.v1",'
        '"result":"ok",'
        '"summary":"second object is valid",'
        '"values_patch":{"replicaCount":2},'
        '"template_patches":[{"file":"templates/deployment.yaml","purpose":"wire","updated_content":"apiVersion: apps/v1\\nkind: Deployment\\n"}],'
        '"violation_coverage":[{"rule_id":"AVL005","status":"addressed","note":"scaled"}],'
        '"warnings":[],"error":""'
        "}"
    )
    parsed = parse_full_fix_response(raw)
    assert parsed.result == "ok"
    assert parsed.values_patch["replicaCount"] == 2
    assert parsed.template_patches[0].updated_content.startswith("apiVersion:")


def test_format_full_fix_preview_markdown_contains_sections() -> None:
    """Full-fix formatter should render values/template/coverage sections."""
    parsed = parse_full_fix_response(
        "{"
        '"schema_version":"full_fix_response.v1",'
        '"result":"ok",'
        '"summary":"fixed",'
        '"values_patch":{"resources":{"requests":{"cpu":"100m"}}},'
        '"template_patches":[{"file":"templates/deployment.yaml","purpose":"wire resources","unified_diff":"--- a/templates/deployment.yaml\\n+++ b/templates/deployment.yaml\\n@@ -1,1 +1,2 @@\\n+resources:"}],'
        '"violation_coverage":[{"rule_id":"RES004","status":"addressed","note":"added requests"}],'
        '"warnings":["review limits"],"error":""'
        "}"
    )
    markdown = format_full_fix_preview_markdown(parsed)
    assert "### AI Full Fix Result" in markdown
    assert "### Violation Coverage" in markdown
    assert "### Values Patch" in markdown
    assert "### Template Patch Preview" in markdown
