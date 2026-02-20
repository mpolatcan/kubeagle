"""Discovery subpackage for TUI screenshot capture.

This subpackage provides functions to discover various interactive elements
in the TUI application, including screens, keyboard bindings, tabs, widgets,
and scrollable content.
"""

from __future__ import annotations

from tui_screenshot_capture.discovery.analyzer import (
    analyze_keyboard_tabs,
    analyze_screen_live,
    analyze_screen_scrollables,
    analyze_scrollbar,
    analyze_tab_scrollables,
    build_discovery_result,
    build_screen_state,
    calculate_scroll_positions,
)
from tui_screenshot_capture.discovery.bindings import (
    discover_focus_targets,
    discover_keyboard_tabs,
    discover_toggles,
)
from tui_screenshot_capture.discovery.screen_parser import (
    get_screen_widgets,
)
from tui_screenshot_capture.discovery.screens import discover_screens
from tui_screenshot_capture.discovery.scrollables import (
    clear_visibility_cache,
    discover_scrollable_widgets,
)
from tui_screenshot_capture.discovery.state import (
    CaptureStatus,
    DiscoveryResult,
    ScreenState,
    ScrollState,
    TabState,
)
from tui_screenshot_capture.discovery.widgets import (
    discover_collapsibles,
    discover_tabbed_content,
    get_widget_stable_id,
)

__all__ = [
    "CaptureStatus",
    "DiscoveryResult",
    "ScreenState",
    "ScrollState",
    "TabState",
    "analyze_keyboard_tabs",
    "analyze_screen_live",
    "analyze_screen_scrollables",
    "analyze_scrollbar",
    "analyze_tab_scrollables",
    "build_discovery_result",
    "build_screen_state",
    "calculate_scroll_positions",
    "clear_visibility_cache",
    "discover_collapsibles",
    "discover_focus_targets",
    "discover_keyboard_tabs",
    "discover_screens",
    "discover_scrollable_widgets",
    "discover_tabbed_content",
    "discover_toggles",
    "get_screen_widgets",
    "get_widget_stable_id",
]
