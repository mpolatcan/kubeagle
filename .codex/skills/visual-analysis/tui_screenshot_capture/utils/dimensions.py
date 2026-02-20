"""Widget dimension calculations for TUI screenshot capture."""

from __future__ import annotations

from typing import Any

from loguru import logger

from tui_screenshot_capture.constants import EMPTY_DIMENSIONS


def _calculate_scrollable_height(content_height: int, viewport_height: int) -> int:
    """Calculate scrollable height from content and viewport dimensions.

    The formula is: scrollable = max(0, content - viewport)
    If content fits within viewport (content <= viewport), scrollable is 0.
    Otherwise, scrollable is the excess content that extends beyond the viewport.

    Args:
        content_height: Total content height in rows.
        viewport_height: Visible viewport height in rows.

    Returns:
        Scrollable height (excess content beyond viewport, 0 if content fits).

    """
    return max(0, content_height - viewport_height)


def _safe_get_region_dimensions(widget: Any) -> tuple[int, int]:
    """Safely get widget region dimensions.

    Args:
        widget: The widget instance.

    Returns:
        Tuple of (viewport_height, viewport_width).
        Both zero if region is not available.
    """
    try:
        region = widget.region
        return (region.height, region.width)
    except AttributeError:
        return (0, 0)


def get_widget_dimensions(widget: Any, widget_type: str) -> dict[str, int]:
    """Get scrollable dimensions for a widget.

    Args:
        widget: The widget instance.
        widget_type: Widget type name (e.g., "DataTable", "ListView").

    Returns:
        dict with 'content_height', 'content_width', 'viewport_height', 'viewport_width',
        'scrollable_height', 'scrollable_width'. Returns zeros if dimensions cannot be determined.

    """
    try:
        # Cache viewport dimensions to avoid repeated attribute access
        viewport_height, viewport_width = _safe_get_region_dimensions(widget)

        # Dispatch based on widget type for specific handling
        if widget_type == "DataTable":
            return _get_datatable_dimensions(widget, viewport_height, viewport_width)
        if widget_type == "ListView":
            return _get_listview_dimensions(widget, viewport_height, viewport_width)

        # Generic scrollable widget - try max_scroll_y / max_scroll_x
        max_y = getattr(widget, "max_scroll_y", 0)
        max_x = getattr(widget, "max_scroll_x", 0)

        return {
            "content_height": max_y + viewport_height if max_y > 0 else viewport_height,
            "content_width": max_x + viewport_width if max_x > 0 else viewport_width,
            "viewport_height": viewport_height,
            "viewport_width": viewport_width,
            "scrollable_height": max_y,
            "scrollable_width": max_x,
        }

    except (AttributeError, TypeError, ValueError) as e:
        # If dimension detection fails, log and return default zeros
        logger.debug(f"Dimension detection failed for {widget_type}: {e}")
        return dict(EMPTY_DIMENSIONS)


def _get_datatable_dimensions(widget: Any, viewport_height: int, viewport_width: int) -> dict[str, int]:
    """Get dimensions for DataTable widget."""
    # Get total row count using direct attribute access
    row_count = getattr(widget, "row_count", None)
    if row_count is not None:
        content_height = row_count
    else:
        rows = getattr(widget, "rows", None)
        content_height = len(rows) if rows else 0

    # Calculate scrollable height
    scrollable_height = _calculate_scrollable_height(content_height, viewport_height)

    # For horizontal scrolling - use max_scroll_x directly
    max_scroll_x = getattr(widget, "max_scroll_x", 0)

    return {
        "content_height": content_height,
        "content_width": 0,
        "viewport_height": viewport_height,
        "viewport_width": viewport_width,
        "scrollable_height": scrollable_height,
        "scrollable_width": max_scroll_x,
    }


def _get_listview_dimensions(widget: Any, viewport_height: int, viewport_width: int) -> dict[str, int]:
    """Get dimensions for ListView widget."""
    content_height = getattr(widget, "row_count", None)
    if content_height is None:
        length = getattr(widget, "len", None)
        content_height = length() if length else 0

    # Handle case where length() returns None
    if content_height is None:
        content_height = 0

    scrollable_height = _calculate_scrollable_height(content_height, viewport_height)

    return {
        "content_height": content_height,
        "content_width": 0,
        "viewport_height": viewport_height,
        "viewport_width": viewport_width,
        "scrollable_height": scrollable_height,
        "scrollable_width": 0,
    }
