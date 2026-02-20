"""CustomContentSwitcher widget - standardized wrapper around Textual's ContentSwitcher."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.containers import Container
from textual.widget import Widget
from textual.widgets import ContentSwitcher as TextualContentSwitcher

if TYPE_CHECKING:
    from textual.app import ComposeResult


class CustomContentSwitcher(Container):
    """Standardized content switcher wrapper around Textual's ContentSwitcher widget.

    Provides consistent styling and integration with the TUI design system.
    Wraps Textual's built-in ContentSwitcher widget with standardized CSS classes.

    CSS Classes: widget-custom-content-switcher

    Example:
        ```python
        with CustomContentSwitcher(classes="widget-custom-content-switcher"):
            yield ContentPanel1()
            yield ContentPanel2()
    ```
    """

    CSS_PATH = "../../css/widgets/custom_content_switcher.tcss"

    def __init__(
        self,
        *children: Widget,
        id: str | None = None,
        classes: str = "",
        initial: str = "",
    ) -> None:
        """Initialize the custom content switcher wrapper.

        Args:
            children: Child widgets to include.
            id: Widget ID.
            classes: CSS classes (widget-custom-content-switcher is automatically added).
            initial: ID of the initial child to show.
        """
        super().__init__(id=id, classes=f"widget-custom-content-switcher {classes}".strip())
        self._children = children
        self._initial = initial

    def compose(self) -> ComposeResult:
        """Compose the content switcher with Textual's ContentSwitcher widget."""
        yield TextualContentSwitcher(
            *self._children,
            id=self.id,
            initial=self._initial,
        )

    @property
    def content_switcher(self) -> TextualContentSwitcher:
        """Get the underlying Textual ContentSwitcher widget.

        Returns:
            The composed Textual ContentSwitcher widget.
        """
        return self.query_one(TextualContentSwitcher)

    @property
    def current(self) -> str | None:
        """Get the currently displayed child widget ID.

        Returns:
            The ID of the current child or None.
        """
        return self.content_switcher.current

    @current.setter
    def current(self, val: str) -> None:
        """Set the currently displayed child widget.

        Args:
            val: ID of the child widget to display.
        """
        self.content_switcher.current = val
