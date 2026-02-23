"""Shared YAML patching utilities with formatting-preserving behavior."""

from __future__ import annotations

import io
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.util import load_yaml_guess_indent

_PATCH_NO_CHANGE = object()


def apply_values_yaml_patch(content: str, patch: dict[str, Any]) -> str:
    """Apply a values patch while rewriting only directly touched key blocks."""
    _, original_doc = _load_roundtrip_yaml_preserving_style(content)
    if original_doc is None:
        original_doc = CommentedMap()
    if not isinstance(original_doc, dict):
        raise ValueError("values.yaml root must be mapping.")

    pruned_patch = _prune_noop_patch(original_doc, patch)
    if pruned_patch is _PATCH_NO_CHANGE:
        return content
    if not isinstance(pruned_patch, dict):
        raise ValueError("values patch root must be mapping.")

    merged_yaml, merged_doc = _load_roundtrip_yaml_preserving_style(content)
    if merged_doc is None:
        merged_doc = CommentedMap()
    if not isinstance(merged_doc, dict):
        raise ValueError("values.yaml root must be mapping.")
    _deep_merge_roundtrip(merged_doc, pruned_patch)

    original_lines = content.splitlines()
    global_indent = _current_yaml_indent(merged_yaml)
    replacements, top_level_additions = _collect_map_replacements(
        original_parent=original_doc,
        merged_parent=merged_doc,
        patch_parent=pruned_patch,
        original_lines=original_lines,
        global_indent=global_indent,
        is_top_level=True,
    )

    updated_lines = list(original_lines)
    for start_line, end_line, replacement_lines in sorted(
        replacements,
        key=lambda item: item[0],
        reverse=True,
    ):
        updated_lines[start_line : end_line + 1] = replacement_lines

    for key in top_level_additions:
        if key not in merged_doc:
            continue
        addition = _dump_single_key_block(merged_yaml, key, merged_doc[key]).strip("\n")
        if updated_lines and updated_lines[-1].strip():
            updated_lines.append("")
        updated_lines.extend(addition.splitlines())

    if not updated_lines:
        return ""
    return "\n".join(updated_lines) + "\n"


def _deep_merge_roundtrip(base: dict[str, Any], override: dict[str, Any]) -> None:
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge_roundtrip(base[key], value)
        else:
            base[key] = value


def _load_roundtrip_yaml_preserving_style(content: str) -> tuple[YAML, Any]:
    ryaml = YAML()
    ryaml.preserve_quotes = True
    ryaml.width = 4096  # prevent long-line wrapping
    loaded, map_indent, block_seq_indent = load_yaml_guess_indent(content, yaml=ryaml)
    _apply_yaml_indent(ryaml, map_indent, block_seq_indent)
    return ryaml, loaded


def _collect_map_replacements(
    *,
    original_parent: dict[str, Any],
    merged_parent: dict[str, Any],
    patch_parent: dict[str, Any],
    original_lines: list[str],
    global_indent: tuple[int | None, int | None],
    is_top_level: bool,
) -> tuple[list[tuple[int, int, list[str]]], list[str]]:
    replacements: list[tuple[int, int, list[str]]] = []
    additions: list[str] = []
    for key, patch_value in patch_parent.items():
        if key not in merged_parent:
            continue
        if key not in original_parent:
            additions.append(key)
            continue

        original_value = original_parent[key]
        merged_value = merged_parent[key]
        if (
            isinstance(patch_value, dict)
            and isinstance(original_value, dict)
            and isinstance(merged_value, dict)
        ):
            nested_replacements, nested_additions = _collect_map_replacements(
                original_parent=original_value,
                merged_parent=merged_value,
                patch_parent=patch_value,
                original_lines=original_lines,
                global_indent=global_indent,
                is_top_level=False,
            )
            if nested_additions:
                replacements.append(
                    _replacement_for_existing_key(
                        original_parent=original_parent,
                        merged_parent=merged_parent,
                        key=key,
                        original_lines=original_lines,
                        global_indent=global_indent,
                    )
                )
            else:
                replacements.extend(nested_replacements)
            continue

        replacements.append(
            _replacement_for_existing_key(
                original_parent=original_parent,
                merged_parent=merged_parent,
                key=key,
                original_lines=original_lines,
                global_indent=global_indent,
            )
        )
    if not is_top_level and additions:
        return replacements, additions
    return replacements, additions


def _replacement_for_existing_key(
    *,
    original_parent: dict[str, Any],
    merged_parent: dict[str, Any],
    key: str,
    original_lines: list[str],
    global_indent: tuple[int | None, int | None],
) -> tuple[int, int, list[str]]:
    key_span = _map_key_span(original_parent, key)
    if key_span is None:
        raise ValueError(f"Unable to locate YAML key span for '{key}'.")
    start_line, end_line, key_column = key_span
    old_block_text = "\n".join(original_lines[start_line : end_line + 1])
    replacement_yaml = _yaml_for_existing_block(old_block_text, global_indent=global_indent)
    replacement_text = _dump_single_key_block(replacement_yaml, key, merged_parent[key])
    replacement_lines = _indent_block_lines(replacement_text.splitlines(), key_column)
    return start_line, end_line, replacement_lines


def _map_key_span(document: dict[str, Any], key: str) -> tuple[int, int, int] | None:
    if not isinstance(document, CommentedMap):
        return None
    key_info = document.lc.data.get(key)
    if not key_info:
        return None
    start_line = int(key_info[0])
    key_column = int(key_info[1]) if len(key_info) > 1 else 0
    value_line = int(key_info[2]) if len(key_info) > 2 else start_line
    end_line = max(start_line, value_line, _max_node_line(document[key]))
    return start_line, end_line, key_column


def _max_node_line(node: Any) -> int:
    max_line = -1
    if isinstance(node, CommentedMap):
        for key, value in node.items():
            key_info = node.lc.data.get(key)
            if key_info:
                max_line = max(max_line, int(key_info[0]))
                if len(key_info) > 2:
                    max_line = max(max_line, int(key_info[2]))
            max_line = max(max_line, _max_node_line(value))
        return max_line
    if isinstance(node, CommentedSeq):
        for index, value in enumerate(node):
            item_info = node.lc.data.get(index)
            if item_info:
                max_line = max(max_line, int(item_info[0]))
            max_line = max(max_line, _max_node_line(value))
        return max_line
    return max_line


def _dump_single_key_block(yaml_obj: YAML, key: str, value: Any) -> str:
    container = CommentedMap()
    container[key] = value
    buf = io.StringIO()
    yaml_obj.dump(container, buf)
    return buf.getvalue().rstrip("\n")


def _indent_block_lines(lines: list[str], indent: int) -> list[str]:
    if indent <= 0:
        return lines
    prefix = " " * indent
    return [f"{prefix}{line}" if line else line for line in lines]


def _yaml_for_existing_block(
    block_text: str,
    *,
    global_indent: tuple[int | None, int | None],
) -> YAML:
    ryaml = YAML()
    ryaml.preserve_quotes = True
    ryaml.width = 4096  # prevent long-line wrapping
    _, map_indent, block_seq_indent = load_yaml_guess_indent(f"{block_text}\n", yaml=ryaml)
    if map_indent is None:
        map_indent = global_indent[0]
    if block_seq_indent is None:
        block_seq_indent = global_indent[1]
    _apply_yaml_indent(ryaml, map_indent, block_seq_indent)
    return ryaml


def _current_yaml_indent(ryaml: YAML) -> tuple[int | None, int | None]:
    map_indent = ryaml.map_indent if isinstance(ryaml.map_indent, int) else None
    sequence_offset = (
        ryaml.sequence_dash_offset if isinstance(ryaml.sequence_dash_offset, int) else None
    )
    return map_indent, sequence_offset


def _apply_yaml_indent(
    ryaml: YAML,
    map_indent: int | None,
    block_seq_indent: int | None,
) -> None:
    if not isinstance(map_indent, int) or map_indent <= 0:
        return
    sequence_offset = block_seq_indent if block_seq_indent is not None else min(2, map_indent)
    sequence_offset = max(0, min(sequence_offset, map_indent))
    ryaml.indent(
        mapping=map_indent,
        sequence=map_indent,
        offset=sequence_offset,
    )


def _prune_noop_patch(current: Any, patch: Any) -> Any:
    if isinstance(patch, dict):
        if not isinstance(current, dict):
            return patch
        pruned: dict[str, Any] = {}
        for key, value in patch.items():
            cur_value = current.get(key, _PATCH_NO_CHANGE)
            next_value = _prune_noop_patch(cur_value, value)
            if next_value is _PATCH_NO_CHANGE:
                continue
            pruned[key] = next_value
        return pruned if pruned else _PATCH_NO_CHANGE
    if _yaml_semantic_equal(current, patch):
        return _PATCH_NO_CHANGE
    return patch


def _yaml_semantic_equal(left: Any, right: Any) -> bool:
    if left is _PATCH_NO_CHANGE:
        return False
    return _canonical_yaml_value(left) == _canonical_yaml_value(right)


def _canonical_yaml_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _canonical_yaml_value(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_canonical_yaml_value(item) for item in value]
    if isinstance(value, str):
        return str(value)
    return value
