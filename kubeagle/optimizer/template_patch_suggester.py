"""Suggestion-only template patch hints for wiring mismatches."""

from __future__ import annotations

import difflib
import textwrap
from pathlib import Path
from typing import Any

from kubeagle.optimizer.llm_patch_protocol import (
    StructuredPatchFile,
    StructuredPatchResponse,
    build_structured_patch_prompt,
    format_structured_patch_preview_markdown,
    parse_structured_patch_response,
)

_PROBE_RULE_IDS = {"PRB001", "PRB002", "PRB003"}


def build_template_patch_suggestions(
    *,
    rule_id: str,
    diagnosis: dict[str, Any],
    fix_payload: dict[str, Any],
    chart_dir: Path | None = None,
) -> list[dict[str, str]]:
    """Create actionable but non-mutating wiring hints."""
    _ = fix_payload
    unmatched_keys: list[str] = list(diagnosis.get("unmatched_keys", []))
    candidate_files: list[str] = list(diagnosis.get("candidate_files", []))
    target_file = candidate_files[0] if candidate_files else "templates/deployment.yaml"
    anchor = _anchor_for_rule(rule_id)
    snippet = _snippet_for_rule(rule_id)
    patch_preview = _build_patch_preview(
        chart_dir=chart_dir,
        target_file=target_file,
        anchor=anchor,
        snippet=snippet,
        rule_id=rule_id,
    )

    suggestions: list[dict[str, str]] = []
    if unmatched_keys:
        reason = "No .Values wiring found for one or more generated fix keys."
        suggestions.append(
            {
                "rule_id": rule_id,
                "file": target_file,
                "anchor": anchor,
                "reason": reason,
                "snippet": snippet,
                "patch_preview": patch_preview,
                "structured_patch_prompt": _build_wiring_prompt(
                    rule_id=rule_id,
                    target_file=target_file,
                    unmatched_keys=unmatched_keys,
                    diagnosis=diagnosis,
                ),
                "structured_patch_response": _build_structured_patch_response_json(
                    file_path=target_file,
                    reason=reason,
                    patch_preview=patch_preview,
                ),
            }
        )
    else:
        reason = "Values keys exist in templates, but rendered output still violates the rule."
        suggestions.append(
            {
                "rule_id": rule_id,
                "file": target_file,
                "anchor": anchor,
                "reason": reason,
                "snippet": snippet,
                "patch_preview": patch_preview,
                "structured_patch_prompt": _build_wiring_prompt(
                    rule_id=rule_id,
                    target_file=target_file,
                    unmatched_keys=[],
                    diagnosis=diagnosis,
                ),
                "structured_patch_response": _build_structured_patch_response_json(
                    file_path=target_file,
                    reason=reason,
                    patch_preview=patch_preview,
                ),
            }
        )
    return suggestions


def format_wiring_suggestions_markdown(suggestions: list[dict[str, str]]) -> str:
    """Render suggestions into compact markdown block."""
    if not suggestions:
        return "No wiring suggestions available."
    chunks: list[str] = []
    for suggestion in suggestions[:3]:
        file_path = str(suggestion.get("file", "templates/deployment.yaml")).replace("`", "'")
        anchor = str(suggestion.get("anchor", "spec.template.spec.containers[0]")).replace("`", "'")
        reason = str(suggestion.get("reason", "")).replace("`", "'")
        snippet = str(suggestion.get("snippet", "")).rstrip()
        patch_preview = str(suggestion.get("patch_preview", "")).rstrip()
        structured_patch_response = str(
            suggestion.get("structured_patch_response", "")
        ).strip()
        chunks.extend(
            [
                f"- **File:** `{file_path}`",
                f"- **Anchor:** `{anchor}`",
                f"- **Reason:** {reason}",
                "```yaml",
                snippet,
                "```",
                "",
            ]
        )
        if structured_patch_response:
            try:
                parsed = parse_structured_patch_response(structured_patch_response)
            except ValueError:
                parsed = None
            if parsed is not None:
                chunks.extend(
                    [
                        "- **Structured Patch:**",
                        "",
                        format_structured_patch_preview_markdown(parsed),
                        "",
                    ]
                )
                continue
        if patch_preview:
            chunks.extend(
                [
                    "- **Patch Preview:**",
                    "```diff",
                    patch_preview,
                    "```",
                    "",
                ]
            )
    return "\n".join(chunks).strip()


def _build_wiring_prompt(
    *,
    rule_id: str,
    target_file: str,
    unmatched_keys: list[str],
    diagnosis: dict[str, Any],
) -> str:
    normalized_rule = (rule_id or "").upper()
    candidate_files = list(diagnosis.get("candidate_files", []))
    allowed_files = [target_file]
    for candidate in candidate_files:
        candidate_file = str(candidate)
        if candidate_file not in allowed_files:
            allowed_files.append(candidate_file)
        if len(allowed_files) >= 3:
            break

    unmatched_value = ", ".join(unmatched_keys) if unmatched_keys else "none"
    task_lines = [
        "Propose a safe Helm template wiring patch for unresolved rendered verification.\n"
        f"Rule ID: {rule_id}",
        f"Primary target file: {target_file}",
        f"Unmatched .Values keys: {unmatched_value}",
    ]
    if normalized_rule in _PROBE_RULE_IDS:
        task_lines.extend(
            [
                "Hard constraints for probe rules:",
                "- Apply probe wiring only under `spec.template.spec.containers[*]`.",
                "- Do NOT add, edit, or move probes under `spec.template.spec.initContainers[*]`.",
                "- Prefer wiring on the primary app container, not init containers.",
            ]
        )
    task_lines.append("Return only the strict JSON contract.")
    task = "\n".join(task_lines)
    return build_structured_patch_prompt(
        task=task,
        allowed_files=allowed_files,
        context_blocks=[
            ("Rule Context", f"rule_id: {rule_id}\nprimary_file: {target_file}"),
            ("Unmatched Keys", unmatched_value),
        ],
    )


def _build_structured_patch_response_json(
    *,
    file_path: str,
    reason: str,
    patch_preview: str,
) -> str:
    patch_preview_value = patch_preview.rstrip()
    if patch_preview_value:
        response = StructuredPatchResponse(
            result="ok",
            summary=reason,
            patches=[
                StructuredPatchFile(
                    file=file_path,
                    purpose="Wire generated values into Helm template.",
                    unified_diff=patch_preview_value,
                )
            ],
            warnings=[],
            error="",
        )
        return response.model_dump_json(indent=2)

    response = StructuredPatchResponse(
        result="error",
        summary=reason,
        patches=[],
        warnings=[
            "Patch preview could not be generated from local template file; review snippet manually."
        ],
        error="No unified diff preview generated for candidate file.",
    )
    return response.model_dump_json(indent=2)


def _snippet_for_rule(rule_id: str) -> str:
    normalized = (rule_id or "").upper()
    if normalized.startswith("RES"):
        return (
            "resources:\n"
            "  requests:\n"
            "    cpu: {{ .Values.resources.requests.cpu | quote }}\n"
            "    memory: {{ .Values.resources.requests.memory | quote }}\n"
            "  limits:\n"
            "    cpu: {{ .Values.resources.limits.cpu | quote }}\n"
            "    memory: {{ .Values.resources.limits.memory | quote }}"
        )
    if normalized == "PRB001":
        return (
            "livenessProbe:\n"
            "{{- toYaml .Values.livenessProbe | nindent 2 }}"
        )
    if normalized == "PRB002":
        return (
            "readinessProbe:\n"
            "{{- toYaml .Values.readinessProbe | nindent 2 }}"
        )
    if normalized == "PRB003":
        return (
            "startupProbe:\n"
            "{{- toYaml .Values.startupProbe | nindent 2 }}"
        )
    if normalized in {"AVL001", "AVL003"}:
        return (
            "apiVersion: policy/v1\n"
            "kind: PodDisruptionBudget\n"
            "metadata:\n"
            "  name: {{ include \"chart.fullname\" . }}\n"
            "spec:\n"
            "  {{- with .Values.podDisruptionBudget }}\n"
            "  {{- toYaml . | nindent 2 }}\n"
            "  {{- end }}"
        )
    if normalized == "AVL002":
        return (
            "affinity:\n"
            "  podAntiAffinity:\n"
            "    preferredDuringSchedulingIgnoredDuringExecution:\n"
            "      - weight: 100\n"
            "        podAffinityTerm:\n"
            "          topologyKey: kubernetes.io/hostname"
        )
    if normalized == "AVL004":
        return (
            "topologySpreadConstraints:\n"
            "{{- toYaml .Values.topologySpreadConstraints | nindent 2 }}"
        )
    if normalized == "AVL005":
        return "replicas: {{ .Values.replicaCount }}"
    if normalized == "SEC001":
        return (
            "securityContext:\n"
            "{{- toYaml .Values.securityContext | nindent 2 }}"
        )
    return (
        "# Wire generated values into template\n"
        "# Example:\n"
        "{{- with .Values }}\n"
        "{{- toYaml . | nindent 2 }}\n"
        "{{- end }}"
    )


def _anchor_for_rule(rule_id: str) -> str:
    normalized = (rule_id or "").upper()
    if normalized in {"AVL001", "AVL003"}:
        return "spec"
    if normalized == "AVL005":
        return "spec.replicas"
    if normalized in {"AVL002", "AVL004"}:
        return "spec.template.spec"
    return "spec.template.spec.containers[0]"


def _build_patch_preview(
    *,
    chart_dir: Path | None,
    target_file: str,
    anchor: str,
    snippet: str,
    rule_id: str,
) -> str:
    if chart_dir is None:
        return ""
    template_path = chart_dir / target_file
    if not template_path.exists():
        return ""
    try:
        original_text = template_path.read_text(encoding="utf-8")
    except OSError:
        return ""

    original_lines = original_text.splitlines()
    insert_at = _find_insert_index(original_lines, anchor, rule_id)
    indented_snippet = _indent_snippet(snippet, original_lines, insert_at, rule_id)
    inserted_lines = indented_snippet.splitlines()
    if not inserted_lines:
        return ""

    modified_lines = original_lines[:insert_at] + inserted_lines + original_lines[insert_at:]
    diff_lines = list(
        difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/{target_file}",
            tofile=f"b/{target_file}",
            lineterm="",
        )
    )
    if not diff_lines:
        return ""
    return "\n".join(diff_lines[:120])


def _find_insert_index(lines: list[str], anchor: str, rule_id: str) -> int:
    normalized = (rule_id or "").upper()
    lower_lines = [line.lower() for line in lines]

    if normalized == "AVL005":
        for index, line in enumerate(lower_lines):
            if "replicas:" in line:
                return index + 1
        for index, line in enumerate(lower_lines):
            if line.strip() == "spec:":
                return index + 1

    if normalized in {"AVL001", "AVL003"}:
        for index, line in enumerate(lower_lines):
            if line.strip() == "spec:":
                return index + 1
        return len(lines)

    if normalized in {"AVL002", "AVL004"}:
        for index, line in enumerate(lower_lines):
            if "topologyspreadconstraints" in line or "affinity:" in line:
                return index + 1
        for index, line in enumerate(lower_lines):
            if "containers:" in line:
                return index

    if normalized.startswith("RES") or normalized in _PROBE_RULE_IDS or normalized == "SEC001":
        container_index = _find_main_containers_index(lower_lines)
        if container_index is not None:
            container_indent = _leading_spaces(lines[container_index])
            for index in range(container_index + 1, len(lines)):
                current_line = lines[index]
                stripped = current_line.strip().lower()
                if not stripped:
                    continue
                current_indent = _leading_spaces(current_line)
                if current_indent <= container_indent:
                    break
                if stripped.startswith("- name:"):
                    return index + 1
            return container_index + 1

    for index, line in enumerate(lower_lines):
        if "- name:" in line:
            return index + 1
    for index, line in enumerate(lower_lines):
        if "containers:" in line and "initcontainers:" not in line:
            return index + 1

    _ = anchor
    return len(lines)


def _indent_snippet(snippet: str, lines: list[str], insert_at: int, rule_id: str) -> str:
    base_indent = 0
    if insert_at > 0:
        previous_line = lines[insert_at - 1]
        base_indent = len(previous_line) - len(previous_line.lstrip(" "))

    normalized = (rule_id or "").upper()
    if normalized in {"AVL001", "AVL003", "AVL005"}:
        indent = max(0, base_indent)
    else:
        indent = max(0, base_indent + 2)

    return textwrap.indent(snippet, " " * indent, lambda line: bool(line.strip()))


def _find_main_containers_index(lower_lines: list[str]) -> int | None:
    for index, lower_line in enumerate(lower_lines):
        stripped = lower_line.strip()
        if stripped.startswith("containers:") and not stripped.startswith("initcontainers:"):
            return index
    return None


def _leading_spaces(line: str) -> int:
    return len(line) - len(line.lstrip(" "))
