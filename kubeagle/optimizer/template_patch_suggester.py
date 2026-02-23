"""Suggestion-only template patch hints for wiring mismatches."""

from __future__ import annotations

from kubeagle.optimizer.llm_patch_protocol import (
    format_structured_patch_preview_markdown,
    parse_structured_patch_response,
)


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
