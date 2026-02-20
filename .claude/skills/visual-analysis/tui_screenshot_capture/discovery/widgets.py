"""Widget discovery for TUI screenshot capture."""

from __future__ import annotations

from typing import Any

from loguru import logger

from tui_screenshot_capture.constants import LABEL_CLEAN_PATTERN_1, LABEL_CLEAN_PATTERN_2
from tui_screenshot_capture.utils import generate_stable_hash


def get_widget_stable_id(widget: Any, label: str = "") -> str:
    """Generate a stable ID for a widget without an explicit ID.

    Args:
        widget: The widget instance.
        label: Optional label to include in the hash (e.g., title).

    Returns:
        Stable ID string in the format '{ClassName}-{hash}'.

    """
    widget_class = widget.__class__.__name__
    parent = getattr(widget, "parent", None)
    parent_id = getattr(parent, "id", "") or "" if parent else ""
    widget_hash = generate_stable_hash(widget_class, parent_id, label)
    return f"{widget_class}-{widget_hash}"


def _get_tab_label(widget: Any, pane_id: str) -> str:
    """Extract clean label for a tab.

    Args:
        widget: The parent TabbedContent or ContentSwitcher widget.
        pane_id: The pane ID to get the label for.

    Returns:
        Clean tab label string.
    """
    try:
        tab = widget.get_tab(pane_id)
        if tab and hasattr(tab, "label"):
            label = _get_text_from_rich_label(tab.label)
            return _clean_tab_label(label)
    except (AttributeError, TypeError, ValueError) as e:
        logger.debug(f"Failed to get label for tab {pane_id}: {e}")
    return pane_id


def _get_text_from_rich_label(label: Any) -> str:
    """Extract plain text from Rich Text label.

    Args:
        label: Rich Text label or string.

    Returns:
        Plain text string.
    """
    if label is None:
        return ""
    if isinstance(label, str):
        return label
    # Handle Textual Rich Text / Text objects
    if hasattr(label, "plain"):
        return label.plain
    # Fallback: try str() which handles most Rich renderable types
    return str(label)


def _clean_tab_label(label: str) -> str:
    """Clean tab label by removing numbers in various formats.

    Examples:
        "All Charts 1" -> "All Charts"
        "All Charts (1)" -> "All Charts"
        "All-Charts-1" -> "All-Charts"
        "By Team 2" -> "By Team"
        "content-1" -> "content"
    """
    # Remove numbers in parentheses at the end: " (1)", "(1)", etc.
    label = LABEL_CLEAN_PATTERN_1.sub("", label)
    # Remove trailing numbers with dash or space: " 1", "-1"
    label = LABEL_CLEAN_PATTERN_2.sub("", label)
    # Clean up any resulting trailing dash
    label = (label or "").rstrip("-").strip()
    return label


def discover_tabbed_content(app: Any) -> list[dict[str, Any]]:
    """Discover TabbedContent and ContentSwitcher widgets in the current screen.

    This function finds widgets that contain multiple tabs or content panes,
    such as TabbedContent (with visible tabs) and ContentSwitcher (without tabs).

    For each discovered widget, returns a dict with:
    - 'widget_id': Widget's ID or generated ID
    - 'widget': The widget instance
    - 'tabs': List of tab info dicts with 'id', 'label', 'index'
    - 'widget_type': 'TabbedContent' or 'ContentSwitcher'
    - 'has_explicit_id': True if widget has explicit ID (affects filename cleanliness)
    - 'widget_index': Index for re-finding after recompose (within filtered batch)

    Args:
        app: The EKSHelmReporterApp instance.

    Returns:
        List of widget info dicts for each TabbedContent/ContentSwitcher found.

    """
    inner_tabs: list[dict[str, Any]] = []

    if not app.screen:
        return inner_tabs

    try:
        # Query for TabbedContent widgets
        tabbed_contents = app.screen.query("TabbedContent")

        # Collect all widget data first (try/except OUTSIDE loop)
        # tuple: (widget, widget_id, tab_panes, tabs_info)
        widget_data_list: list[tuple[Any, str, list[Any], list[dict[str, Any]]]] = []
        for widget in tabbed_contents:
            explicit_id = getattr(widget, "id", None)
            if explicit_id:
                widget_id = explicit_id
            else:
                widget_id = get_widget_stable_id(widget)

            # Method 1: Query TabPane children to get real pane IDs
            tab_panes: list[Any] = []
            try:
                tab_panes = widget.query("TabPane")
            except (AttributeError, TypeError) as e:
                logger.debug(f"Failed to query TabPane children: {e}")

            # Method 2: Fallback to Tabs widget children (also collected outside loop processing)
            tabs_info: list[dict[str, Any]] = []
            try:
                tabs_widget = widget.query_one("Tabs")
                for i, tab in enumerate(tabs_widget.query("Tab")):
                    tab_id = getattr(tab, "id", None)
                    if tab_id:
                        # Tab id is usually like "--content-tab-{pane_id}"
                        # The pane_id is after the last dash
                        pane_id = tab_id
                        if "--content-tab-" in tab_id:
                            pane_id = tab_id.replace("--content-tab-", "")
                        raw_label = getattr(tab, "label", pane_id)
                        label = _get_text_from_rich_label(raw_label)
                        label = _clean_tab_label(label)
                        tabs_info.append(
                            {
                                "id": pane_id,
                                "label": label,
                                "index": i,
                            }
                        )
            except (AttributeError, ValueError) as e:
                logger.warning(f"Failed to query Tabs widget: {e}")

            widget_data_list.append((widget, widget_id, tab_panes, tabs_info))

        # Process collected data without try/except inside loop
        for widget, widget_id, tab_panes, tabs_info in widget_data_list:
            # Process tab panes using list comprehension for performance
            if not tabs_info:
                tabs_info = [
                    {
                        "id": pane_id,
                        "label": _get_tab_label(widget, pane_id),
                        "index": i,
                    }
                    for i, pane in enumerate(tab_panes)
                    if (pane_id := getattr(pane, "id", None) or f"tab-{i}")
                ]

            # Method 3: Try _tab_content (internal attribute)
            if not tabs_info and hasattr(widget, "_tab_content"):
                for pane_id in widget._tab_content.keys():
                    label = _get_tab_label(widget, pane_id)
                    tabs_info.append(
                        {
                            "id": pane_id,
                            "label": label,
                        }
                    )

            if tabs_info:
                inner_tabs.append(
                    {
                        "widget_id": widget_id,
                        "widget": widget,
                        "tabs": tabs_info,
                        "widget_type": "TabbedContent",
                        # Store explicit ID if set, otherwise None
                        "has_explicit_id": getattr(widget, "id", None) is not None,
                    }
                )
    except (AttributeError, TypeError) as e:
        logger.warning(f"Failed to query TabbedContent widgets: {e}")

    # Also check for ContentSwitcher widgets
    try:
        content_switchers = app.screen.query("ContentSwitcher")
        for widget in content_switchers:
            explicit_id = getattr(widget, "id", None)
            if explicit_id:
                widget_id = explicit_id
            else:
                widget_id = get_widget_stable_id(widget)

            try:
                children = widget.children
            except AttributeError:
                children = []

            if children:
                # Build tabs info using list comprehension for performance
                tabs_info = [
                    {
                        "id": (child_id := getattr(child, "id", f"content-{i}")),
                        "label": _get_child_label(child, child_id),
                        "index": i,
                    }
                    for i, child in enumerate(children)
                ]

                if tabs_info:
                    inner_tabs.append(
                        {
                            "widget_id": widget_id,
                            "widget": widget,
                            "widget_type": "ContentSwitcher",
                            "tabs": tabs_info,
                            "has_explicit_id": getattr(widget, "id", None) is not None,
                        }
                    )
    except (AttributeError, TypeError) as e:
        logger.debug(f"Failed to query ContentSwitcher widgets: {e}")

    return inner_tabs


def _get_child_label(child: Any, fallback_id: str) -> str:
    """Extract label from child widget with multiple fallback sources.

    Args:
        child: The child widget to extract label from.
        fallback_id: ID to use if no label sources are available.

    Returns:
        Clean tab label string.
    """
    label = (
        getattr(child, "label", None)
        or getattr(child, "renderable", None)
        or getattr(child, "title", None)
        or fallback_id
    )
    return _clean_tab_label(_get_text_from_rich_label(label))


def discover_collapsibles(app: Any) -> list[dict[str, Any]]:
    """Discover Collapsible widgets in the current screen.

    Each returned dict contains:
    - 'id': Widget's ID or generated ID
    - 'title': Collapsible title text
    - 'collapsed': True if currently collapsed
    - 'widget': The widget instance

    Args:
        app: The EKSHelmReporterApp instance.

    Returns:
        List of collapsible widget info dicts.

    """
    collapsibles: list[dict[str, Any]] = []
    seen_widgets: set[int] = set()  # Track by widget id to avoid duplicates

    if not app.screen:
        return collapsibles

    try:
        widgets = app.screen.query("Collapsible")
        for widget in widgets:
            widget_obj_id = id(widget)
            if widget_obj_id in seen_widgets:
                continue
            seen_widgets.add(widget_obj_id)

            try:
                explicit_id = getattr(widget, "id", None)
                widget_title = getattr(widget, "title", "")
                if explicit_id:
                    widget_id = explicit_id
                else:
                    widget_id = get_widget_stable_id(widget, label=widget_title)
                widget_collapsed = getattr(widget, "collapsed", True)
                collapsibles.append(
                    {
                        "id": widget_id,
                        "title": widget_title,
                        "collapsed": widget_collapsed,
                        "widget": widget,
                    }
                )
            except (AttributeError, ValueError, RuntimeError):
                logger.debug("Failed to process collapsible widget")
    except (AttributeError, TypeError) as e:
        logger.debug(f"Failed to query Collapsible widgets: {e}")

    return collapsibles
