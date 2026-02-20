"""Screen discovery for TUI screenshot capture."""

from __future__ import annotations

from functools import lru_cache

from kubeagle.keyboard import GLOBAL_BINDINGS

from tui_screenshot_capture.constants import SCREEN_ALIAS_MAP


@lru_cache(maxsize=1)
def discover_screens() -> dict[str, str]:
    """Discover all available screens from the app.

    Returns:
        dict mapping screen_name -> navigation_key (key to press).

    Note:
        Results are cached since screen bindings don't change at runtime.

    """
    # Global navigation bindings that start with "nav_"
    screens_by_key = {
        action.replace("nav_", ""): key
        for key, action, _ in GLOBAL_BINDINGS
        if action.startswith("nav_")
    }

    # Add home screen (default)
    screens_by_key["home"] = "h"

    # Add aliases from SCREEN_ALIAS_MAP (for reverse lookups)
    # Only add if canonical exists and alias doesn't already exist
    screens_by_key.update(
        {alias: screens_by_key[canonical]
         for alias, canonical in SCREEN_ALIAS_MAP.items()
         if canonical in screens_by_key and alias not in screens_by_key}
    )

    return screens_by_key
