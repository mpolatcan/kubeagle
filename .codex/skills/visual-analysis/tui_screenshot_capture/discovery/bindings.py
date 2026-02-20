"""Keyboard binding discovery for TUI screenshot capture."""

from __future__ import annotations

from functools import lru_cache

from kubeagle.keyboard import (
    CHART_DETAIL_SCREEN_BINDINGS,
    CHARTS_EXPLORER_SCREEN_BINDINGS,
    CLUSTER_SCREEN_BINDINGS,
    OPTIMIZER_SCREEN_BINDINGS,
    REPORT_EXPORT_SCREEN_BINDINGS,
    SETTINGS_SCREEN_BINDINGS,
)
from loguru import logger

from tui_screenshot_capture.constants import (
    MIN_REPLACE_PARTS,
    MIXED_QUOTE_PATTERN,
    REPLACE_PREFIX_LEN,
    REPLACE_TRANSFORM_PATTERN,
    get_canonical_name,
)

# Map canonical screen names to their binding lists
SCREEN_BINDINGS_MAP = {
    "home": CLUSTER_SCREEN_BINDINGS,
    "cluster": CLUSTER_SCREEN_BINDINGS,
    "charts_explorer": CHARTS_EXPLORER_SCREEN_BINDINGS,
    "charts": CHARTS_EXPLORER_SCREEN_BINDINGS,
    "chart_detail": CHART_DETAIL_SCREEN_BINDINGS,
    "optimizer": OPTIMIZER_SCREEN_BINDINGS,
    "recommendations": OPTIMIZER_SCREEN_BINDINGS,
    "export": REPORT_EXPORT_SCREEN_BINDINGS,
    "settings": SETTINGS_SCREEN_BINDINGS,
}


@lru_cache(maxsize=32)
def _discover_screen_bindings(screen_name: str) -> list[dict[str, str]]:
    """Discover all keybindings for a specific screen.

    Args:
        screen_name: Name of the screen (can be an alias).

    Returns:
        list of dicts with 'key', 'action', and 'description'.

    """
    # Resolve alias to canonical name
    canonical_name = get_canonical_name(screen_name)

    if canonical_name not in SCREEN_BINDINGS_MAP:
        logger.debug(
            f"Unknown screen name: {screen_name} (canonical: {canonical_name})"
        )
        return []

    bindings = SCREEN_BINDINGS_MAP[canonical_name]
    # Convert binding tuples to dicts using list comprehension
    return [
        {"key": key, "action": action, "description": description}
        for key, action, description in bindings
    ]


def _parse_replace_transform(transform: str, action: str) -> str:
    """Parse replace(old, new) transform and apply to action.

    Args:
        transform: Transform string in format "replace('old', 'new')" or 'replace("old", "new")'.
        action: The action string to transform.

    Returns:
        Transformed string with old substring replaced by new.

    """
    # Use pre-compiled regex to parse replace(old, new) with non-greedy matching and mixed quote support
    match = REPLACE_TRANSFORM_PATTERN.match(transform)
    if match:
        old, new = match.groups()
        if old:
            return action.replace(old, new)
        return action

    # Fallback: extract content between parentheses if regex didn't match
    if transform.startswith("replace(") and transform.endswith(")"):
        inner = transform[REPLACE_PREFIX_LEN:-1]  # Remove replace( and )

        # Handle both quote styles (including mixed quotes)
        if '", "' in inner:
            old, new = inner.split('", ', 1)
        elif "', '" in inner:
            old, new = inner.split("', ", 1)
        elif '"' in inner and "'" in inner:
            # Mixed quote styles: try to parse with a more robust approach
            mixed_match = MIXED_QUOTE_PATTERN.match(inner)
            if mixed_match:
                old, new = mixed_match.groups()
            else:
                return action
        else:
            # Generic split and validate parts exist
            parts = inner.split(", ")
            if len(parts) >= MIN_REPLACE_PARTS and all(p.strip() for p in parts[:2]):
                old, new = parts[0], parts[1]
            else:
                return action

        # Strip quotes from old and new values
        old = old.strip().strip("'\"")
        new = new.strip().strip("'\"")
        return action.replace(old, new)

    return action


def _discover_by_action(
    screen_name: str,
    action_prefix: str,
    name_transform: str | None = None,
) -> list[dict[str, str]]:
    """Generic helper to discover bindings by action prefix.

    Args:
        screen_name: Name of the screen.
        action_prefix: Action prefix to filter by (e.g., "switch_tab", "focus", "toggle").
        name_transform: Optional transformation to apply to action to get name.
            - "replace(old, new)": Replace 'old' substring with 'new'
            - Other values used as-is

    Returns:
        list of dicts with 'key', 'action', and name field for each matching binding.

    """
    bindings = _discover_screen_bindings(screen_name)

    return [
        {
            "key": binding["key"],
            "action": f"action_{binding['action']}",
            "description": binding["description"],
            "name": (
                _parse_replace_transform(name_transform, binding["action"])
                if name_transform and name_transform.startswith("replace(")
                else binding["action"]
            ),
        }
        for binding in bindings
        if binding["action"].startswith(action_prefix)
    ]


def discover_keyboard_tabs(screen_name: str) -> list[dict[str, str]]:
    """Discover tabs available on a screen by reading keyboard bindings.

    Args:
        screen_name: Name of the screen.

    Returns:
        list of dicts with 'key', 'action', and 'name' for each tab.

    """
    return _discover_by_action(
        screen_name,
        action_prefix="switch_tab",
        name_transform="replace('switch_tab_', '')",
    )


def discover_focus_targets(screen_name: str) -> list[dict[str, str]]:
    """Discover focusable targets for a screen.

    Args:
        screen_name: Name of the screen.

    Returns:
        list of dicts with 'key', 'action', 'target' (not 'name') for each focus target.
        Uses 'target' instead of 'name' to distinguish focus targets from other naming.

    """
    result = _discover_by_action(
        screen_name,
        action_prefix="focus",
        name_transform="replace('focus_', '')",
    )
    # Rename 'name' to 'target' for focus targets (non-mutating)
    return [
        {
            "key": item["key"],
            "action": item["action"],
            "target": item["name"],
            "description": item["description"],
        }
        for item in result
    ]


def discover_toggles(screen_name: str) -> list[dict[str, str]]:
    """Discover toggle states for a screen.

    Args:
        screen_name: Name of the screen.

    Returns:
        list of dicts with 'key', 'action', 'name' for each toggle.
        Uses 'name' instead of 'target' to distinguish toggles from focus targets.

    """
    return _discover_by_action(
        screen_name,
        action_prefix="toggle",
        name_transform="replace('toggle_', '')",
    )
