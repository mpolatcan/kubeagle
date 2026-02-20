"""TUI Screenshot Capture Package.

Comprehensive screenshot capture tool for Textual TUI applications with advanced
features for visual testing and documentation.
"""

from __future__ import annotations

from tui_screenshot_capture.cli import app, create_app
from tui_screenshot_capture.core import CaptureConfig, CaptureResult, TuiCaptureError
from tui_screenshot_capture.discovery import (
    CaptureStatus,
    DiscoveryResult,
    ScreenState,
    ScrollState,
    TabState,
    analyze_keyboard_tabs,
    build_discovery_result,
    discover_collapsibles,
    discover_focus_targets,
    discover_keyboard_tabs,
    discover_screens,
    discover_scrollable_widgets,
    discover_tabbed_content,
    discover_toggles,
    get_widget_stable_id,
)
from tui_screenshot_capture.engine import CaptureEngine
from tui_screenshot_capture.utils import (
    convert_svg_to_png,
    get_widget_dimensions,
    parse_delays_safe,
    parse_size_safe,
)

__all__ = [
    "CaptureConfig",
    "CaptureEngine",
    "CaptureResult",
    "CaptureStatus",
    "DiscoveryResult",
    "ScreenState",
    "ScrollState",
    "TabState",
    "TuiCaptureError",
    "analyze_keyboard_tabs",
    "app",
    "build_discovery_result",
    "convert_svg_to_png",
    "create_app",
    "discover_collapsibles",
    "discover_focus_targets",
    "discover_keyboard_tabs",
    "discover_screens",
    "discover_scrollable_widgets",
    "discover_tabbed_content",
    "discover_toggles",
    "get_widget_dimensions",
    "get_widget_stable_id",
    "parse_delays_safe",
    "parse_size_safe",
]
