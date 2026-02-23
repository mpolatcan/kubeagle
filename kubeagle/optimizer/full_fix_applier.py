"""Apply full-fix bundles (values + template diffs) atomically."""

from __future__ import annotations

import contextlib
import hashlib
import os
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any

import yaml

from kubeagle.optimizer.llm_patch_protocol import FullFixTemplatePatch
from kubeagle.optimizer.yaml_patcher import apply_values_yaml_patch

_HUNK_HEADER_PATTERN = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? \+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@"
)

_CHART_LOCKS: dict[str, Lock] = {}
_CHART_LOCKS_GUARD = Lock()


@dataclass(slots=True)
class FullFixApplyResult:
    """Result object for full fix atomic apply operations."""

    ok: bool
    status: str  # ok|error
    note: str = ""
    touched_files: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def parse_template_patches_from_bundle_diff(
    *,
    diff_text: str,
    allowed_files: set[str] | None = None,
) -> list[FullFixTemplatePatch]:
    """Parse multi-file unified diff text into structured template patches."""
    lines = diff_text.splitlines()
    patches: list[FullFixTemplatePatch] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.startswith("--- "):
            i += 1
            continue
        if i + 1 >= len(lines) or not lines[i + 1].startswith("+++ "):
            raise ValueError("Malformed unified diff: expected +++ line after ---.")
        start = i
        i += 2
        while i < len(lines):
            if (
                lines[i].startswith("--- ")
                and i + 1 < len(lines)
                and lines[i + 1].startswith("+++ ")
            ):
                break
            i += 1
        chunk = lines[start:i]
        file_path = _extract_patch_file_path(chunk[1])
        _validate_relative_template_path(file_path)
        if allowed_files is not None and file_path not in allowed_files:
            raise ValueError(f"Patch file is outside allowed set: {file_path}")
        patches.append(
            FullFixTemplatePatch(
                file=file_path,
                purpose="Edited from bundle diff",
                unified_diff="\n".join(chunk).rstrip(),
            )
        )
    return patches


def apply_unified_diff_to_text(
    *,
    original_text: str,
    unified_diff: str,
) -> str:
    """Apply a single-file unified diff to original text."""
    original_had_trailing_newline = original_text.endswith("\n")
    original_lines = original_text.splitlines()
    diff_lines = unified_diff.splitlines()
    hunks = _parse_hunks(diff_lines)

    updated = list(original_lines)
    offset = 0
    for hunk in hunks:
        start_idx = hunk.old_start - 1 + offset
        if start_idx < 0:
            raise ValueError("Invalid hunk start index.")
        idx = start_idx
        replacement: list[str] = []
        for body_line in hunk.lines:
            if not body_line:
                raise ValueError("Malformed hunk line: empty.")
            prefix = body_line[0]
            text = body_line[1:]
            if prefix == " ":
                if idx >= len(updated) or updated[idx] != text:
                    raise ValueError("Hunk context does not match target file.")
                replacement.append(text)
                idx += 1
                continue
            if prefix == "-":
                if idx >= len(updated) or updated[idx] != text:
                    raise ValueError("Hunk removal does not match target file.")
                idx += 1
                continue
            if prefix == "+":
                replacement.append(text)
                continue
            if prefix == "\\":
                # e.g. "\ No newline at end of file"
                continue
            raise ValueError(f"Unsupported hunk prefix: {prefix}")
        updated[start_idx:idx] = replacement
        offset += len(replacement) - (idx - start_idx)

    merged = "\n".join(updated)
    if updated and original_had_trailing_newline:
        merged += "\n"
    return merged


def apply_full_fix_bundle_atomic(
    *,
    chart_dir: Path,
    values_path: Path,
    values_patch: dict[str, Any],
    template_patches: list[FullFixTemplatePatch],
) -> FullFixApplyResult:
    """Apply values patch + template patches atomically with in-memory rollback."""
    chart_dir = chart_dir.expanduser().resolve()
    values_path = values_path.expanduser().resolve()
    lock = _chart_lock(chart_dir)
    with lock:
        snapshots: dict[Path, bytes] = {}
        touched_files: list[str] = []
        try:
            # Template patches first
            for patch in template_patches:
                rel_path = str(patch.file).strip()
                _validate_relative_template_path(rel_path)
                target_path = (chart_dir / rel_path).resolve()
                if not str(target_path).startswith(str(chart_dir)):
                    raise ValueError(f"Patch path escapes chart directory: {rel_path}")
                if not target_path.exists():
                    raise ValueError(f"Patch target file not found: {rel_path}")
                original = target_path.read_text(encoding="utf-8")
                if patch.updated_content.strip():
                    updated = patch.updated_content
                    if updated and not updated.endswith("\n"):
                        updated = f"{updated}\n"
                else:
                    try:
                        updated = apply_unified_diff_to_text(
                            original_text=original,
                            unified_diff=patch.unified_diff,
                        )
                    except ValueError as exc:
                        raise ValueError(f"{rel_path}: {exc!s}") from exc
                if target_path not in snapshots:
                    snapshots[target_path] = target_path.read_bytes()
                target_path.write_text(updated, encoding="utf-8")
                touched_files.append(str(target_path))

            # Values patch
            if values_patch:
                raw_values = values_path.read_text(encoding="utf-8")
                updated_values = apply_values_yaml_patch(raw_values, values_patch)
                if values_path not in snapshots:
                    snapshots[values_path] = values_path.read_bytes()
                values_path.write_text(updated_values, encoding="utf-8")
                touched_files.append(str(values_path))

            return FullFixApplyResult(
                ok=True,
                status="ok",
                note="Full fix bundle applied successfully.",
                touched_files=touched_files,
            )
        except Exception as exc:
            _restore_file_snapshots(snapshots)
            return FullFixApplyResult(
                ok=False,
                status="error",
                note=f"Failed to apply full fix bundle: {exc!s}",
                touched_files=touched_files,
                errors=[str(exc)],
            )


def apply_full_fix_bundle_via_staged_replace(
    *,
    chart_dir: Path,
    values_path: Path,
    values_patch: dict[str, Any],
    template_patches: list[FullFixTemplatePatch],
) -> FullFixApplyResult:
    """Stage edits in temp chart copy, then atomically replace touched originals."""
    chart_dir = chart_dir.expanduser().resolve()
    values_path = values_path.expanduser().resolve()
    lock = _chart_lock(chart_dir)
    with lock:
        try:
            rel_values_path = _resolve_values_relative_path(chart_dir=chart_dir, values_path=values_path)
            touched_rel_paths: list[str] = []
            for patch in template_patches:
                rel_path = str(patch.file).strip()
                _validate_relative_template_path(rel_path)
                target_path = (chart_dir / rel_path).resolve()
                if not str(target_path).startswith(str(chart_dir)):
                    raise ValueError(f"Patch path escapes chart directory: {rel_path}")
                if not target_path.exists():
                    raise ValueError(f"Patch target file not found: {rel_path}")
                touched_rel_paths.append(rel_path)
            if values_patch:
                touched_rel_paths.append(rel_values_path.as_posix())
            touched_rel_paths = _dedupe_ordered_paths(touched_rel_paths)
            if not touched_rel_paths:
                return FullFixApplyResult(
                    ok=True,
                    status="ok",
                    note="No file changes requested by full fix bundle.",
                )

            source_hashes: dict[str, str] = {}
            for rel_path in touched_rel_paths:
                target_path = (chart_dir / rel_path).resolve()
                if not str(target_path).startswith(str(chart_dir)):
                    raise ValueError(f"Target path escapes chart directory: {rel_path}")
                if not target_path.exists():
                    raise ValueError(f"Target file not found: {rel_path}")
                source_hashes[rel_path] = _hash_file_sha256(target_path)

            with tempfile.TemporaryDirectory(prefix="kubeagle-full-fix-apply-") as tmp_dir:
                staged_chart_dir = Path(tmp_dir) / chart_dir.name
                shutil.copytree(chart_dir, staged_chart_dir)
                staged_values_path = staged_chart_dir / rel_values_path
                if not staged_values_path.exists():
                    raise ValueError("Staged values file path could not be resolved.")

                staged_apply_result = apply_full_fix_bundle_atomic(
                    chart_dir=staged_chart_dir,
                    values_path=staged_values_path,
                    values_patch=values_patch,
                    template_patches=template_patches,
                )
                if not staged_apply_result.ok:
                    return FullFixApplyResult(
                        ok=False,
                        status="error",
                        note=f"Failed to stage full fix bundle: {staged_apply_result.note}",
                        errors=list(staged_apply_result.errors),
                    )

                for rel_path, expected_hash in source_hashes.items():
                    target_path = (chart_dir / rel_path).resolve()
                    if not target_path.exists():
                        return FullFixApplyResult(
                            ok=False,
                            status="error",
                            note=f"Target file changed during apply: {rel_path}",
                            errors=[f"{rel_path}: file missing before promote"],
                        )
                    current_hash = _hash_file_sha256(target_path)
                    if current_hash != expected_hash:
                        return FullFixApplyResult(
                            ok=False,
                            status="error",
                            note=(
                                "Apply aborted: chart files changed while staging edits. "
                                "Regenerate and re-verify before applying."
                            ),
                            errors=[f"{rel_path}: source hash changed"],
                        )

                snapshots: dict[Path, bytes] = {}
                touched_files: list[str] = []
                try:
                    for rel_path in touched_rel_paths:
                        target_path = (chart_dir / rel_path).resolve()
                        staged_path = (staged_chart_dir / rel_path).resolve()
                        if not staged_path.exists():
                            raise ValueError(f"Staged file missing for promote: {rel_path}")
                        if target_path not in snapshots:
                            snapshots[target_path] = target_path.read_bytes()
                        _replace_with_atomic_copy(staged_path=staged_path, target_path=target_path)
                        touched_files.append(str(target_path))
                except Exception as exc:
                    _restore_file_snapshots(snapshots)
                    return FullFixApplyResult(
                        ok=False,
                        status="error",
                        note=f"Failed to promote staged full fix bundle: {exc!s}",
                        touched_files=touched_files,
                        errors=[str(exc)],
                    )
                return FullFixApplyResult(
                    ok=True,
                    status="ok",
                    note="Full fix bundle applied from staged workspace.",
                    touched_files=touched_files,
                )
        except Exception as exc:
            return FullFixApplyResult(
                ok=False,
                status="error",
                note=f"Failed to apply staged full fix bundle: {exc!s}",
                errors=[str(exc)],
            )


def promote_staged_workspace_atomic(
    *,
    chart_dir: Path,
    staged_chart_dir: Path,
    changed_rel_paths: list[str],
    source_hashes: dict[str, str],
) -> FullFixApplyResult:
    """Promote edited files from staged chart copy into original chart atomically."""
    chart_dir = chart_dir.expanduser().resolve()
    staged_chart_dir = staged_chart_dir.expanduser().resolve()
    lock = _chart_lock(chart_dir)
    with lock:
        try:
            rel_paths = _dedupe_ordered_paths(changed_rel_paths)
            if not rel_paths:
                return FullFixApplyResult(
                    ok=True,
                    status="ok",
                    note="No staged file changes to promote.",
                )
            for rel_path in rel_paths:
                _validate_relative_chart_path(rel_path)
                target_path = (chart_dir / rel_path).resolve()
                staged_path = (staged_chart_dir / rel_path).resolve()
                if not str(target_path).startswith(str(chart_dir)):
                    raise ValueError(f"Target path escapes chart directory: {rel_path}")
                if not str(staged_path).startswith(str(staged_chart_dir)):
                    raise ValueError(f"Staged path escapes staged chart directory: {rel_path}")
                if not target_path.exists():
                    raise ValueError(f"Target file not found before promote: {rel_path}")
                if not staged_path.exists():
                    raise ValueError(f"Staged file missing for promote: {rel_path}")
                if rel_path not in source_hashes:
                    raise ValueError(f"Missing source hash for file: {rel_path}")
                current_hash = _hash_file_sha256(target_path)
                if current_hash != source_hashes[rel_path]:
                    raise ValueError(
                        "Apply aborted: source file changed since preview generation "
                        f"({rel_path}). Regenerate and re-verify."
                    )

            snapshots: dict[Path, bytes] = {}
            touched_files: list[str] = []
            try:
                for rel_path in rel_paths:
                    target_path = (chart_dir / rel_path).resolve()
                    staged_path = (staged_chart_dir / rel_path).resolve()
                    if target_path not in snapshots:
                        snapshots[target_path] = target_path.read_bytes()
                    _replace_with_atomic_copy(staged_path=staged_path, target_path=target_path)
                    touched_files.append(str(target_path))
            except Exception as exc:
                _restore_file_snapshots(snapshots)
                return FullFixApplyResult(
                    ok=False,
                    status="error",
                    note=f"Failed to promote staged workspace: {exc!s}",
                    touched_files=touched_files,
                    errors=[str(exc)],
                )

            return FullFixApplyResult(
                ok=True,
                status="ok",
                note="Staged workspace promoted successfully.",
                touched_files=touched_files,
            )
        except Exception as exc:
            return FullFixApplyResult(
                ok=False,
                status="error",
                note=f"Failed to promote staged workspace: {exc!s}",
                errors=[str(exc)],
            )


def parse_values_patch_yaml(values_patch_text: str) -> dict[str, Any]:
    """Parse YAML text from editor into values patch mapping."""
    parsed = yaml.safe_load(values_patch_text.strip() or "{}")
    if parsed is None:
        return {}
    if not isinstance(parsed, dict):
        raise ValueError("Values patch editor content must be a YAML mapping.")
    return parsed


def _restore_file_snapshots(snapshots: dict[Path, bytes]) -> None:
    for path, content in snapshots.items():
        with contextlib.suppress(OSError):
            path.write_bytes(content)


def _replace_with_atomic_copy(*, staged_path: Path, target_path: Path) -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    temp_target = target_path.with_name(f"{target_path.name}.staged.{timestamp}")
    shutil.copy2(staged_path, temp_target)
    try:
        os.replace(temp_target, target_path)
    finally:
        with contextlib.suppress(OSError):
            if temp_target.exists():
                temp_target.unlink()


def _hash_file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve_values_relative_path(*, chart_dir: Path, values_path: Path) -> Path:
    try:
        rel_values_path = values_path.relative_to(chart_dir)
    except ValueError as exc:
        raise ValueError("Values file is outside chart directory.") from exc
    rel_posix = rel_values_path.as_posix()
    if rel_values_path.is_absolute() or ".." in rel_values_path.parts:
        raise ValueError(f"Values file path is not safe for staging: {rel_posix}")
    return rel_values_path


def _dedupe_ordered_paths(paths: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(key)
    return deduped


@dataclass(slots=True)
class _Hunk:
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[str]


def _parse_hunks(diff_lines: list[str]) -> list[_Hunk]:
    hunks: list[_Hunk] = []
    i = 0
    while i < len(diff_lines):
        line = diff_lines[i]
        if not line.startswith("@@ "):
            i += 1
            continue
        match = _HUNK_HEADER_PATTERN.match(line)
        if not match:
            raise ValueError(f"Malformed hunk header: {line}")
        old_start = int(match.group("old_start"))
        old_count = int(match.group("old_count") or "1")
        new_start = int(match.group("new_start"))
        new_count = int(match.group("new_count") or "1")
        i += 1
        body: list[str] = []
        while i < len(diff_lines) and not diff_lines[i].startswith("@@ "):
            if diff_lines[i].startswith("--- ") and i + 1 < len(diff_lines) and diff_lines[i + 1].startswith("+++ "):
                break
            body.append(diff_lines[i])
            i += 1
        hunks.append(
            _Hunk(
                old_start=old_start,
                old_count=old_count,
                new_start=new_start,
                new_count=new_count,
                lines=body,
            )
        )
    if not hunks:
        raise ValueError("No hunks found in unified diff.")
    return hunks


def _extract_patch_file_path(plus_line: str) -> str:
    if not plus_line.startswith("+++ "):
        raise ValueError("Malformed unified diff: missing +++ header line.")
    raw = plus_line[4:].strip()
    if raw.startswith("b/"):
        return raw[2:]
    if raw.startswith("a/"):
        return raw[2:]
    return raw


def _validate_relative_chart_path(rel_path: str) -> None:
    path = Path(rel_path)
    if path.is_absolute():
        raise ValueError(f"Absolute paths are not allowed: {rel_path}")
    if ".." in path.parts:
        raise ValueError(f"Path traversal is not allowed: {rel_path}")


def _validate_relative_template_path(rel_path: str) -> None:
    path = Path(rel_path)
    if path.is_absolute():
        raise ValueError(f"Absolute paths are not allowed: {rel_path}")
    if ".." in path.parts:
        raise ValueError(f"Path traversal is not allowed: {rel_path}")
    if not rel_path.startswith("templates/"):
        raise ValueError(f"Only templates/ files are allowed: {rel_path}")


def _chart_lock(chart_dir: Path) -> Lock:
    key = str(chart_dir)
    with _CHART_LOCKS_GUARD:
        if key not in _CHART_LOCKS:
            _CHART_LOCKS[key] = Lock()
        return _CHART_LOCKS[key]
