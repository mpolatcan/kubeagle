"""CustomTabs wrapper widget - standardized wrapper around Textual's Tabs."""

from __future__ import annotations

from collections.abc import Callable

from textual.widgets import Tab as TextualTab, Tabs as TextualTabs


class CustomTab(TextualTab):
    """Wrapper around Textual's Tab with standardized styling.

    The native ``Tab.label`` property (returns ``Content``, accepts
    ``ContentText``) is preserved -- do NOT override it.  Use
    ``label_text`` for a plain-string accessor.

    CSS Classes: widget-custom-tab
    """

    CSS_PATH = "../../css/widgets/custom_tabs.tcss"

    def __init__(
        self,
        label: str,
        id: str | None = None,
        disabled: bool = False,
        classes: str = "",
    ) -> None:
        """Initialize the custom tab.

        Args:
            label: Tab label text.
            id: Widget ID.
            disabled: Whether the tab is disabled.
            classes: CSS classes.
        """
        self._label_text = label
        super().__init__(
            label=label,
            id=id,
            disabled=disabled,
            classes=f"widget-custom-tab {classes}".strip(),
        )

    @property
    def label_text(self) -> str:
        """Get the tab label as a plain string.

        Returns:
            The label text.
        """
        return self._label_text


class CustomTabs(TextualTabs):
    """Standardized tabs wrapper around Textual's Tabs widget.

    Provides consistent styling and integration with the TUI design system.
    Wraps Textual's built-in Tabs widget with standardized CSS classes.

    CSS Classes: widget-custom-tabs

    Note:
        This class wraps Textual's Tabs widget for standardized styling.
        For the context manager-based tab system, use CustomTabContainer from
        the navigation module.

    Example:
        ```python
        CustomTabs(id="main-tabs", classes="widget-custom-tabs")
    ```
    """

    CSS_PATH = "../../css/widgets/custom_tabs.tcss"

    def __init__(
        self,
        id: str | None = None,
        classes: str = "",
        tabs: list[dict[str, str]] | None = None,
        active: str | None = None,
        on_change: Callable[[str], None] | None = None,
    ) -> None:
        """Initialize the custom tabs wrapper.

        Args:
            id: Widget ID.
            classes: CSS classes (widget-custom-tabs is automatically added).
            tabs: List of tab definitions with 'id' and 'label' keys.
            active: ID of the initially active tab.
            on_change: Callback when active tab changes.
        """
        super().__init__(id=id, classes=f"widget-custom-tabs {classes}".strip())
        self._tabs_config = tabs or []
        self._active = active
        self._on_change = on_change

    def on_mount(self) -> None:
        """Mount and configure tabs."""
        # Add tabs from configuration
        for tab_config in self._tabs_config:
            tab = CustomTab(
                label=tab_config.get("label", ""),
                id=tab_config.get("id") or None,
                disabled=bool(tab_config.get("disabled", False)),
            )
            self.add_tab(tab)

        # Set active tab if specified
        if self._active:
            self.active = self._active

    def create_tab(self, label: str, disabled: bool = False) -> CustomTab:
        """Create a new CustomTab with the given label.

        Args:
            label: Tab label text.
            disabled: Whether the tab is disabled.

        Returns:
            The created CustomTab widget.
        """
        return CustomTab(label=label, disabled=disabled)

    def on_tabs_tab_activated(self, event: TextualTabs.TabActivated) -> None:
        """Forward native tab activation to optional callback."""
        if self._on_change is None:
            return
        tab_id = str(event.tab.id or "")
        if tab_id:
            self._on_change(tab_id)
