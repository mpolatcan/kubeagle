"""Scrollable widget discovery for TUI screenshot capture."""

from __future__ import annotations

import threading
from typing import Any

from loguru import logger

from tui_screenshot_capture.constants import (
    CACHE_EVICTION_MIN_ITEMS,
    EXCLUDED_TYPES,
    MAX_PARENT_ITERATIONS,
    MAX_SCROLLABLES_CACHE_SIZE,
    MAX_VISIBILITY_CACHE_SIZE,
    MIN_HORIZONTAL_SCROLL_PIXELS,
    MIN_VERTICAL_SCROLL_ROWS,
    SCROLLABLE_TYPE_NAMES,
    SCROLLABLE_TYPES,
    SCROLLABLES_CACHE_EVICTION_COUNT,
    SKIP_PARENT_CLASSES,
)

# Cache for widget visibility checks to avoid repeated parent traversal
# Thread-safe access via lock
_visibility_cache: dict[int, bool] = {}
_visibility_cache_lock = threading.Lock()


def _evict_oldest_visibility_cache_entries() -> None:
    """Evict oldest entries from visibility cache when over limit.

    Uses FIFO eviction (removes first-inserted items).
    Thread-safe: must be called with lock held.
    """
    evict_count = max(len(_visibility_cache) // 10, CACHE_EVICTION_MIN_ITEMS)
    for _ in range(evict_count):
        try:
            first_key = next(iter(_visibility_cache))
            del _visibility_cache[first_key]
        except (StopIteration, KeyError):
            break


def _is_widget_visible(widget: Any) -> bool:
    """Check if a widget is visible (not hidden in a non-active tab).

    This specifically checks for TabPane parents which Textual uses to hide
    content in non-active tabs.

    Uses caching by widget object id to avoid repeated parent traversal.

    Args:
        widget: The widget to check.

    Returns:
        True if the widget is visible, False otherwise.

    """
    widget_id = id(widget)

    # Check cache first with proper thread-safe read
    with _visibility_cache_lock:
        cached_visibility = _visibility_cache.get(widget_id)
        if cached_visibility is not None:
            return cached_visibility

    try:
        # Fast path: check widget's own display attribute first
        if getattr(widget, "display", True) is False:
            with _visibility_cache_lock:
                _visibility_cache[widget_id] = False
            return False

        # Check if any parent is a hidden TabPane or has display=False
        # TabPane sets display=False when it's not the active tab
        parent = getattr(widget, "parent", None)
        iterations = 0
        while parent is not None and iterations < MAX_PARENT_ITERATIONS:
            iterations += 1
            # Use try/except for faster attribute access when attribute exists
            try:
                parent_display = parent.display
                if parent_display is False:
                    with _visibility_cache_lock:
                        _visibility_cache[widget_id] = False
                    return False
            except AttributeError:
                pass

            # Get parent reference directly from the current parent object
            # This is more reliable than getattr in a loop
            try:
                parent = parent.parent
            except AttributeError:
                parent = None

        is_visible = True
    except (AttributeError, TypeError) as e:
        logger.debug(f"Widget visibility check failed: {e}")
        is_visible = True  # If we can't determine, assume visible

    with _visibility_cache_lock:
        _visibility_cache[widget_id] = is_visible
        if len(_visibility_cache) > MAX_VISIBILITY_CACHE_SIZE:
            _evict_oldest_visibility_cache_entries()
    return is_visible


def clear_visibility_cache() -> None:
    """Clear the widget visibility cache.

    Call this when navigating between screens or when widget visibility
    may have changed (e.g., after tab switch).
    """
    with _visibility_cache_lock:
        _visibility_cache.clear()


# Cache for scrollable widget discovery keyed by (screen_id, primary_only)
# Using dict with max size to store list results (lru_cache requires hashable types)
_scrollables_cache: dict[tuple[int, bool], list[dict[str, Any]]] = {}
_scrollables_cache_lock = threading.Lock()


def _evict_oldest_scrollable_cache_entries(count: int = SCROLLABLES_CACHE_EVICTION_COUNT) -> None:
    """Evict multiple oldest entries from the scrollables cache.

    Uses FIFO eviction (removes first-inserted items).

    Args:
        count: Number of entries to evict.
    """
    for _ in range(count):
        try:
            # FIFO eviction: get first key and delete it
            # (dict maintains insertion order in Python 3.7+)
            first_key = next(iter(_scrollables_cache))
            del _scrollables_cache[first_key]
        except (StopIteration, KeyError):
            break


def _discover_scrollables_impl(
    app: Any, primary_only: bool
) -> list[dict[str, Any]]:
    """Internal implementation of scrollable widget discovery.

    Returns list of widget info dicts for compatibility with analyzer code
    that calls .get() on elements.

    Args:
        app: The EKSHelmReporterApp instance.
        primary_only: If True, only return primary content widgets.

    Returns:
        List of widget info dicts with keys:
        'id', 'type', 'widget', 'scroll_x', 'scroll_y', 'has_explicit_id'.
    """
    scrollable_widgets: list[dict[str, Any]] = []
    seen_widgets: set[int] = set()  # Track by widget id to avoid duplicates

    if not app.screen:
        return []

    def add_widget(
        widget: Any, widget_type: str, scroll_x: bool, scroll_y: bool
    ) -> None:
        """Add widget to list if not already present and not excluded."""
        widget_obj_id = id(widget)
        if widget_obj_id in seen_widgets:
            return

        # Skip excluded types
        if widget_type in EXCLUDED_TYPES:
            return

        # If primary_only, skip non-primary content types
        if primary_only and widget_type not in SCROLLABLE_TYPE_NAMES:
            return

        # Skip hidden widgets (those in non-active tabs)
        if not _is_widget_visible(widget):
            return

        # Skip widgets whose parent is in SKIP_PARENT_CLASSES (e.g., Footer's internal scrollable)
        parent = getattr(widget, "parent", None)
        if parent is not None:
            parent_class = parent.__class__.__name__
            if parent_class in SKIP_PARENT_CLASSES:
                logger.debug(f"Skipping widget inside {parent_class}: {widget_type}")
                return

        seen_widgets.add(widget_obj_id)

        explicit_id = getattr(widget, "id", None)
        widget_id = explicit_id or f"synthetic-{widget_type}-{widget_obj_id}"
        scrollable_widgets.append(
            {
                "id": widget_id,
                "type": widget_type,
                "widget": widget,
                "scroll_x": scroll_x,
                "scroll_y": scroll_y,
                # Track whether widget has explicit ID for cleaner filenames
                "has_explicit_id": explicit_id is not None,
            }
        )

    # Check screen-level scrollability first
    # The screen itself can be scrollable if content overflows
    screen = app.screen
    try:
        max_scroll_y = getattr(screen, "max_scroll_y", 0) or 0
        max_scroll_x = getattr(screen, "max_scroll_x", 0) or 0
        has_screen_scroll_y = max_scroll_y >= MIN_VERTICAL_SCROLL_ROWS
        has_screen_scroll_x = max_scroll_x >= MIN_HORIZONTAL_SCROLL_PIXELS

        if has_screen_scroll_y or has_screen_scroll_x:
            screen_id = getattr(screen, "id", None) or "screen"
            seen_widgets.add(id(screen))
            scrollable_widgets.append(
                {
                    "id": screen_id,
                    "type": "Screen",
                    "widget": screen,
                    "scroll_x": has_screen_scroll_x,
                    "scroll_y": has_screen_scroll_y,
                    "has_explicit_id": getattr(screen, "id", None) is not None,
                }
            )
            logger.debug(
                f"Screen is scrollable: scroll_y={max_scroll_y}, scroll_x={max_scroll_x}"
            )
    except (AttributeError, TypeError) as e:
        logger.debug(f"Failed to check screen scrollability: {e}")

    # Query for primary content widget types
    # Optimization: Pre-query all widgets in batch to avoid repeated queries
    # This pattern avoids PERF203 by moving try-except outside inner loop
    for type_name, (selector, scroll_x, scroll_y) in SCROLLABLE_TYPES.items():
        try:
            widgets = screen.query(selector)
        except (AttributeError, TypeError) as e:
            logger.debug(f"Failed to query {type_name} widgets: {e}")
            continue  # Skip to next type on error

        # Early exit if no widgets found (optimization)
        if not widgets:
            continue

        # Process widgets outside try-except for performance
        for widget in widgets:
            add_widget(widget, type_name, scroll_x, scroll_y)

    return scrollable_widgets


def discover_scrollable_widgets(
    app: Any, primary_only: bool = True
) -> list[dict[str, Any]]:
    """Discover scrollable widgets in the current screen.

    Focuses on PRIMARY content widgets that users actually want to scroll through.
    Only returns widgets that are currently VISIBLE (not in hidden tabs).

    This function uses internal caching keyed by screen id and primary_only flag.
    Results are cached per screen context to avoid repeated discovery overhead.

    Args:
        app: The EKSHelmReporterApp instance.
        primary_only: If True (default), only return primary content widgets
            (DataTable, ListView, Tree, OptionList). If False, include all
            scrollable widgets.

    Returns:
        List of widget info dicts with keys:
        'id', 'type', 'widget', 'scroll_x', 'scroll_y', 'has_explicit_id'.

    """
    if not app.screen:
        return []

    # Use screen id as cache key (screen id changes when navigating between screens)
    screen_id = id(app.screen)
    cache_key = (screen_id, primary_only)

    # Check cache first
    with _scrollables_cache_lock:
        if cache_key in _scrollables_cache:
            return _scrollables_cache[cache_key]

    # Discover and cache the result
    result = _discover_scrollables_impl(app, primary_only)

    # Store in cache with size limit enforcement
    with _scrollables_cache_lock:
        _scrollables_cache[cache_key] = result
        # Evict oldest entries if cache exceeds max size
        if len(_scrollables_cache) > MAX_SCROLLABLES_CACHE_SIZE:
            _evict_oldest_scrollable_cache_entries(SCROLLABLES_CACHE_EVICTION_COUNT)

    return result
