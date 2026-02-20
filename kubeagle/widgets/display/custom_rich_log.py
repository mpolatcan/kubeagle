"""CustomRichLog widget - standardized wrapper around Textual's RichLog."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.containers import Container
from textual.widgets import RichLog as TextualRichLog

if TYPE_CHECKING:
    from textual.app import ComposeResult


class CustomRichLog(Container):
    """Standardized rich log wrapper around Textual's RichLog widget.

    Provides consistent styling and integration with the TUI design system.
    Wraps Textual's built-in RichLog widget with standardized CSS classes.

    CSS Classes: widget-custom-rich-log

    Example:
        ```python
        CustomRichLog(
            id="log-viewer",
            classes="widget-custom-rich-log"
        )
    ```
    """

    CSS_PATH = "../../css/widgets/custom_rich_log.tcss"

    def __init__(
        self,
        id: str | None = None,
        classes: str = "",
        disabled: bool = False,
        highlight: bool = False,
        markup: bool = True,
        wrap: bool = True,
        max_lines: int | None = None,
    ) -> None:
        """Initialize the custom rich log wrapper.

        Args:
            id: Widget ID.
            classes: CSS classes (widget-custom-rich-log is automatically added).
            disabled: Whether the rich log is disabled.
            highlight: Whether to highlight links.
            markup: Whether to enable Rich markup rendering.
            wrap: Whether to wrap long lines.
            max_lines: Maximum number of lines to display.
        """
        super().__init__(id=id, classes=f"widget-custom-rich-log {classes}".strip())
        self._disabled = disabled
        self._highlight = highlight
        self._markup = markup
        self._wrap = wrap
        self._max_lines = max_lines
        self._inner_widget: TextualRichLog | None = None

    def compose(self) -> ComposeResult:
        """Compose the rich log with Textual's RichLog widget."""
        inner_id = f"{self.id}-inner" if self.id else None
        widget = TextualRichLog(
            id=inner_id,
            disabled=self._disabled,
            highlight=self._highlight,
            markup=self._markup,
            wrap=self._wrap,
            max_lines=self._max_lines,
        )
        self._inner_widget = widget
        yield widget

    @property
    def rich_log(self) -> TextualRichLog | None:
        """Get the underlying Textual RichLog widget.

        Returns:
            The composed Textual RichLog widget, or None if not yet composed.
        """
        return self._inner_widget

    def write(self, *args, **kwargs) -> None:
        """Write to the rich log.

        Args:
            *args: Arguments to write.
            **kwargs: Keyword arguments for write.
        """
        if self._inner_widget is not None:
            self._inner_widget.write(*args, **kwargs)

    def write_line(self, *args, **kwargs) -> None:
        """Write a line to the rich log.

        Args:
            *args: Arguments to write.
            **kwargs: Keyword arguments for write.
        """
        # RichLog doesn't have write_line, use write() instead
        if self._inner_widget is not None:
            self._inner_widget.write(*args, **kwargs)

    def clear(self) -> None:
        """Clear the rich log."""
        if self._inner_widget is not None:
            self._inner_widget.clear()

    @property
    def disabled(self) -> bool:
        """Get the disabled state.

        Returns:
            True if disabled, False otherwise.
        """
        if self._inner_widget is None:
            return self._disabled
        return self._inner_widget.disabled

    @disabled.setter
    def disabled(self, val: bool) -> None:
        """Set the disabled state.

        Args:
            val: New disabled state.
        """
        self._disabled = val
        if self._inner_widget is not None:
            self._inner_widget.disabled = val
