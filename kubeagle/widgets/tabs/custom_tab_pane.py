"""CustomTabPane widget - standardized direct extension of Textual's TabPane."""

from __future__ import annotations

from typing import Any

from textual.widget import Widget
from textual.widgets._tabbed_content import TabPane as TextualTabPane


class CustomTabPane(TextualTabPane):
    """Standardized tab pane extending Textual's TabPane widget.

    Provides consistent styling and integration with the TUI design system.
    Directly inherits from Textual's built-in TabPane widget so that
    TabbedContent recognizes it as a real TabPane during composition.

    CSS Classes: widget-custom-tab-pane

    Example:
        ```python
        with CustomTabPane("Tab Label", id="tab-id"):
            yield SomeContent()
        ```
    """

    CSS_PATH = "../../css/widgets/custom_tab_pane.tcss"

    def __init__(
        self,
        *args: Any,
        label: str = "",
        id: str | None = None,
        classes: str = "",
        disabled: bool = False,
    ) -> None:
        """Initialize the custom tab pane.

        Supports two calling conventions:
        1. ``CustomTabPane("Label", widget1, widget2, id="tab-id")`` -- first
           positional string becomes the title, remaining positional args are
           child widgets.
        2. ``CustomTabPane(widget1, label="Label", id="tab-id")`` -- title
           supplied via *label* keyword.

        Args:
            *args: Positional arguments.  If the first argument is a string it
                is treated as the tab title; all remaining positional arguments
                are child widgets passed to the parent TabPane.
            label: Tab label text (used when the title is not given as a
                positional string).
            id: Widget ID.
            classes: CSS classes (widget-custom-tab-pane is automatically added).
            disabled: Whether the tab pane is disabled.
        """
        # Separate title from child widgets in positional args
        title: str = label
        children: list[Widget] = []

        if args and isinstance(args[0], str):
            title = args[0]
            children = list(args[1:])
        elif args:
            children = list(args)

        super().__init__(
            title,
            *children,
            id=id,
            classes=f"widget-custom-tab-pane {classes}".strip(),
            disabled=disabled,
        )

        # Store for backward-compatible access
        self._widgets: tuple[Any, ...] = tuple(children)

    # ------------------------------------------------------------------
    # Backward-compatible properties
    # ------------------------------------------------------------------

    @property
    def _label(self) -> str:
        """Return the tab title as a plain string.

        Returns:
            The label text.
        """
        return str(self._title)

    @property
    def _disabled(self) -> bool:
        """Return the disabled state (backward-compatible accessor).

        Returns:
            True if disabled, False otherwise.
        """
        return self.disabled

    @property
    def label(self) -> str:
        """Get the tab label.

        Returns:
            The label text.
        """
        return str(self._title)

    @label.setter
    def label(self, val: str) -> None:
        """Set the tab label.

        Args:
            val: New label text.
        """
        self._title = self.render_str(val)
