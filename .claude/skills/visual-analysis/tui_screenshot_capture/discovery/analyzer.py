"""Screen analyzer for comprehensive discovery."""

from __future__ import annotations

from itertools import chain
from typing import Any

from tui_screenshot_capture.constants import (
    DEFAULT_SCROLL_STEPS,
    MIN_HORIZONTAL_SCROLL_PIXELS,
    MIN_VERTICAL_SCROLL_ROWS,
)
from tui_screenshot_capture.discovery.bindings import (
    discover_focus_targets,
    discover_keyboard_tabs,
    discover_toggles,
)
from tui_screenshot_capture.discovery.screens import discover_screens
from tui_screenshot_capture.discovery.scrollables import discover_scrollable_widgets
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
from tui_screenshot_capture.utils import get_widget_dimensions


def _build_scroll_state(
    widget_id: str,
    widget: Any,
    widget_type: str,
    has_explicit_id: bool,
) -> ScrollState:
    """Build ScrollState from widget dimensions.

    Args:
        widget_id: The widget identifier.
        widget: The widget instance.
        widget_type: Type name of the widget.
        has_explicit_id: Whether widget has explicit ID.

    Returns:
        ScrollState with computed scrollbar information.

    """
    dimensions = get_widget_dimensions(widget, widget_type)
    scroll_state = ScrollState(
        widget_id=widget_id,
        widget_type=widget_type,
        content_height=dimensions.get("content_height", 0),
        content_width=dimensions.get("content_width", 0),
        viewport_height=dimensions.get("viewport_height", 0),
        viewport_width=dimensions.get("viewport_width", 0),
        max_scroll_y=dimensions.get("scrollable_height", 0),
        max_scroll_x=dimensions.get("scrollable_width", 0),
        has_explicit_id=has_explicit_id,
        widget=widget,  # Store widget reference directly
    )

    # Determine if scrollbars are actually needed
    scroll_state.has_vertical = scroll_state.max_scroll_y >= MIN_VERTICAL_SCROLL_ROWS
    scroll_state.has_horizontal = scroll_state.max_scroll_x >= MIN_HORIZONTAL_SCROLL_PIXELS

    # Calculate scroll positions if scrollable
    if scroll_state.has_vertical:
        scroll_state.scroll_positions_v = calculate_scroll_positions(
            scroll_state.max_scroll_y
        )
    if scroll_state.has_horizontal:
        scroll_state.scroll_positions_h = calculate_scroll_positions(
            scroll_state.max_scroll_x
        )

    return scroll_state


def analyze_scrollbar(
    widget: Any, widget_type: str
) -> ScrollState:
    """Analyze a widget to determine its actual scrollbar state.

    Args:
        widget: The widget instance.
        widget_type: Type name of the widget.

    Returns:
        ScrollState with actual scrollbar information.

    """
    # Get widget ID - use explicit ID if available, otherwise generate stable identifier
    widget_id = getattr(widget, "id", None)
    if widget_id:
        return _build_scroll_state(widget_id, widget, widget_type, True)

    # Try query_path for stable identification
    query_path = getattr(widget, "query_path", None)
    if query_path:
        widget_id = f"{widget_type}-{query_path}"
        return _build_scroll_state(widget_id, widget, widget_type, False)

    # Generate stable ID based on widget properties
    widget_label = getattr(widget, "label", "") or ""
    widget_id = get_widget_stable_id(widget, label=widget_label)
    return _build_scroll_state(widget_id, widget, widget_type, False)


def calculate_scroll_positions(
    max_scroll: int, steps: int = DEFAULT_SCROLL_STEPS
) -> list[int]:
    """Calculate evenly distributed scroll positions.

    Args:
        max_scroll: Maximum scroll value.
        steps: Number of intermediate positions to capture (default 5).
            Captures at: 20%, 40%, 60%, 80%, 100% of scroll range.
            Position 0% is excluded (base screenshot is captured separately).

    Returns:
        List of scroll positions (unique, evenly distributed from 1 to max_scroll).

    """
    if max_scroll <= 0:
        return []

    if steps <= 1:
        return []

    # Generate scroll positions using integer division for even distribution
    # Positions are: (i * max_scroll) // steps for i in 1..steps
    # This gives evenly spaced positions from 1 to max_scroll without floats
    positions = [(i * max_scroll) // steps for i in range(1, steps + 1)]
    # Remove duplicates (can happen when max_scroll < steps) while preserving order
    return list(dict.fromkeys(positions))


def analyze_screen_scrollables(
    app: Any, primary_only: bool = True
) -> list[ScrollState]:
    """Analyze all scrollable widgets in the current screen.

    Args:
        app: The EKSHelmReporterApp instance.
        primary_only: If True (default), only return primary content widgets
            (DataTable, ListView, Tree, etc.). If False, include all scrollable widgets.

    Returns:
        List of ScrollState for each scrollable widget.

    """
    scrollables = discover_scrollable_widgets(app, primary_only=primary_only)
    scroll_states = [
        analyze_scrollbar(
            widget=widget,
            widget_type=w.get("type", "Unknown"),
        )
        for w in scrollables
        if (widget := w.get("widget"))
    ]

    return scroll_states


def _analyze_inner_tabs(app: Any) -> list[TabState]:
    """Analyze TabbedContent/ContentSwitcher widgets.

    Args:
        app: The EKSHelmReporterApp instance.

    Returns:
        List of TabState for each inner tab widget.

    """
    inner_tabs_raw = discover_tabbed_content(app)
    return [
        TabState(
            tab_id=tab.get("id", ""),
            tab_name=tab.get("label") or tab.get("id", ""),
            tab_index=tab.get("index", 0),
        )
        for widget_info in inner_tabs_raw
        for tab in widget_info.get("tabs", [])
    ]


def analyze_keyboard_tabs(screen_name: str) -> list[TabState]:
    """Analyze keyboard-accessible tabs for a screen.

    Args:
        screen_name: Name of the screen.

    Returns:
        List of TabState for each keyboard tab.

    """
    tabs_raw = discover_keyboard_tabs(screen_name)
    return [
        TabState(
            tab_id=tab.get("action", ""),
            tab_name=tab.get("name", ""),
            tab_key=tab.get("key"),
            tab_index=idx,
        )
        for idx, tab in enumerate(tabs_raw)
    ]


def build_screen_state(
    app: Any,
    screen_name: str,
    nav_key: str,
    is_current: bool = False,
) -> ScreenState:
    """Build complete state for a screen.

    Args:
        app: The EKSHelmReporterApp instance.
        screen_name: Name of the screen.
        nav_key: Keyboard key to navigate to this screen.
        is_current: Whether this is the currently active screen.

    Returns:
        Complete ScreenState with all discovered elements.

    """
    screen_state = ScreenState(
        screen_name=screen_name,
        nav_key=nav_key,
        is_current=is_current,
    )

    # Discover keyboard tabs
    screen_state.keyboard_tabs = analyze_keyboard_tabs(screen_name)

    # If we're on this screen, do live discovery
    if is_current and app.screen:
        # Discover scrollables
        screen_state.scrollables = analyze_screen_scrollables(app)

        # Discover inner tabs
        screen_state.inner_tabs = _analyze_inner_tabs(app)

        # Discover collapsibles
        screen_state.collapsibles = discover_collapsibles(app)

        # Discover focus targets and toggles (from bindings, not live)
        # Cache results to avoid duplicate calls
        screen_state.focus_targets = discover_focus_targets(screen_name)
        screen_state.toggles = discover_toggles(screen_name)

    # Calculate total captures needed
    screen_state.total_captures = _calculate_total_captures(screen_state)

    return screen_state


def _count_scroll_positions(scrollables: list[ScrollState]) -> int:
    """Count scroll positions for a list of scrollables."""
    return sum(
        len(scroll_state.scroll_positions_v) + len(scroll_state.scroll_positions_h)
        for scroll_state in scrollables
        if scroll_state.has_vertical or scroll_state.has_horizontal
    )


def _calculate_total_captures(screen_state: ScreenState) -> int:
    """Calculate total number of captures needed for a screen.

    This counts:
    - 1 base screenshot
    - Scroll positions for screen-level scrollables
    - 1 screenshot per keyboard tab + its scroll positions
    - 1 screenshot per inner tab + its scroll positions
    - 2 states (on/off) per toggle
    - 1 screenshot per focus target
    - 2 states (expanded/collapsed) per collapsible

    Args:
        screen_state: The screen state to calculate captures for.

    Returns:
        Total number of screenshots needed.

    """
    # Calculate total tabs without creating intermediate list
    total_tabs = len(screen_state.keyboard_tabs) + len(screen_state.inner_tabs)

    # Single-pass calculation for tab scroll positions
    tab_scroll_total = sum(
        _count_scroll_positions(tab.scrollables)
        for tab in chain(screen_state.keyboard_tabs, screen_state.inner_tabs)
    )

    return (
        1  # Base screenshot
        + _count_scroll_positions(screen_state.scrollables)  # Screen scrollables
        + total_tabs  # All tab screenshots (keyboard + inner)
        + tab_scroll_total  # All tab scrollables (single pass)
        + len(screen_state.toggles) * 2  # Toggle states
        + len(screen_state.focus_targets)  # Focus states
        + len(screen_state.collapsibles) * 2  # Collapsible states
    )


def build_discovery_result() -> DiscoveryResult:
    """Build initial discovery result with all screens.

    Returns:
        DiscoveryResult with all screens in PENDING status.

    """
    result = DiscoveryResult()
    screens = discover_screens()

    for screen_name, nav_key in screens.items():
        screen_state = ScreenState(
            screen_name=screen_name,
            nav_key=nav_key,
            status=CaptureStatus.PENDING,
        )

        # Add binding-based info (available without running app)
        screen_state.keyboard_tabs = analyze_keyboard_tabs(screen_name)
        screen_state.focus_targets = discover_focus_targets(screen_name)
        screen_state.toggles = discover_toggles(screen_name)

        result.add_screen(screen_state)

    return result


def analyze_screen_live(
    app: Any,
    screen_name: str,
    nav_key: str,
) -> ScreenState:
    """Analyze a screen with live app instance.

    This should be called when the app is on the target screen.

    Args:
        app: The EKSHelmReporterApp instance (must be on target screen).
        screen_name: Name of the screen.
        nav_key: Keyboard key to navigate to this screen.

    Returns:
        Complete ScreenState with live-discovered elements.

    """
    return build_screen_state(app, screen_name, nav_key, is_current=True)


def analyze_tab_scrollables(
    app: Any,
    tab_state: TabState,
) -> TabState:
    """Analyze scrollables within a tab context.

    Should be called after switching to the tab.

    Args:
        app: The EKSHelmReporterApp instance.
        tab_state: The tab state to update.

    Returns:
        Updated TabState with scrollable information.

    """
    tab_state.scrollables = analyze_screen_scrollables(app)
    tab_state.is_active = True
    return tab_state
