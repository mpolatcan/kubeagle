"""Template wiring diagnosis for unresolved fix outcomes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

_WORKLOAD_NAME_HINTS = (
    "deployment",
    "statefulset",
    "daemonset",
    "cronjob",
    "job",
)

_WORKLOAD_KIND_HINTS = (
    "kind: deployment",
    "kind: statefulset",
    "kind: daemonset",
    "kind: cronjob",
    "kind: job",
)

_RULE_PDB_IDS = {"AVL001", "AVL003"}
_RULE_WORKLOAD_IDS = {"AVL002", "AVL004", "AVL005"}
_RULE_CONTAINER_IDS = {"SEC001", "PRB001", "PRB002", "PRB003"}


def diagnose_template_wiring(
    *,
    chart_dir: Path,
    fix_payload: dict[str, Any],
    rule_id: str = "",
) -> dict[str, Any]:
    """Inspect chart templates and report value-key wiring coverage."""
    templates_dir = chart_dir / "templates"
    if not templates_dir.exists():
        return {
            "templates_found": False,
            "template_files": [],
            "key_matches": {},
            "unmatched_keys": flatten_fix_paths(fix_payload),
            "candidate_files": [],
        }

    template_files = sorted(path for path in templates_dir.rglob("*") if path.is_file())
    keys = flatten_fix_paths(fix_payload)
    key_matches: dict[str, list[str]] = {key: [] for key in keys}
    template_contents: dict[str, str] = {}

    for template_file in template_files:
        try:
            content = template_file.read_text(encoding="utf-8")
        except OSError:
            continue
        rel_path = str(template_file.relative_to(chart_dir))
        template_contents[rel_path] = content
        for key in keys:
            patterns = _key_patterns(key)
            if any(pattern in content for pattern in patterns):
                key_matches[key].append(rel_path)

    unmatched_keys = [key for key, matches in key_matches.items() if not matches]
    candidate_files = _discover_candidate_files(
        template_contents=template_contents,
        key_matches=key_matches,
        fix_keys=keys,
        rule_id=rule_id,
    )

    return {
        "templates_found": True,
        "template_files": sorted(template_contents.keys()),
        "key_matches": key_matches,
        "unmatched_keys": unmatched_keys,
        "candidate_files": candidate_files,
    }


def flatten_fix_paths(payload: dict[str, Any], prefix: str = "") -> list[str]:
    """Flatten dict keys to dot notation for .Values path lookup."""
    paths: list[str] = []
    for key, value in payload.items():
        current_key = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            paths.extend(flatten_fix_paths(value, current_key))
        elif isinstance(value, list):
            paths.append(current_key)
        else:
            paths.append(current_key)
    return sorted(set(paths))


def _key_patterns(key: str) -> tuple[str, ...]:
    if "." not in key:
        return (
            f".Values.{key}",
            f'index .Values "{key}"',
        )
    segments = key.split(".")
    jsonpath = "".join(f'["{segment}"]' for segment in segments)
    return (
        f".Values.{key}",
        f".Values{jsonpath}",
        f'index .Values "{segments[0]}"',
    )


def _discover_candidate_files(
    *,
    template_contents: dict[str, str],
    key_matches: dict[str, list[str]],
    fix_keys: list[str],
    rule_id: str,
) -> list[str]:
    scored: list[tuple[int, str]] = []
    normalized_rule = (rule_id or "").upper()

    for rel_path, content in template_contents.items():
        lower_rel = rel_path.lower()
        lower_content = content.lower()
        if not lower_rel.endswith((".yaml", ".yml", ".tpl")):
            continue

        score = 0
        matches_for_file = sum(1 for paths in key_matches.values() if rel_path in paths)
        score += matches_for_file * 40

        if "_helpers.tpl" in lower_rel:
            score -= 80
        elif lower_rel.endswith(".tpl"):
            score -= 20

        if any(hint in lower_rel for hint in _WORKLOAD_NAME_HINTS):
            score += 25
        if any(hint in lower_content for hint in _WORKLOAD_KIND_HINTS):
            score += 20

        score += _rule_specific_score(normalized_rule, lower_rel, lower_content)

        if any(_looks_related_to_fix_key(key, lower_content) for key in fix_keys):
            score += 10

        scored.append((score, rel_path))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [path for _, path in scored[:5]]


def _rule_specific_score(rule_id: str, rel_path: str, content: str) -> int:
    if rule_id in _RULE_PDB_IDS:
        if "poddisruptionbudget" in content or "pdb" in rel_path:
            return 60
        return -10

    if rule_id in _RULE_WORKLOAD_IDS:
        signal = 0
        if "template:" in content and "spec:" in content:
            signal += 20
        if "affinity:" in content or "topologyspreadconstraints" in content:
            signal += 15
        if "replica" in content:
            signal += 10
        return signal

    if rule_id.startswith("RES") or rule_id in _RULE_CONTAINER_IDS:
        signal = 0
        if "containers:" in content:
            signal += 25
        if "resources:" in content or "securitycontext" in content:
            signal += 10
        return signal

    return 0


def _looks_related_to_fix_key(key: str, content: str) -> bool:
    top_level = key.split(".", 1)[0].lower()
    return (
        f".values.{top_level}" in content
        or f"{top_level}:" in content
    )
