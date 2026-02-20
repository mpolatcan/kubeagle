"""CustomTextArea widget - standardized wrapper around Textual's TextArea."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.containers import Container
from textual.widgets import TextArea as TextualTextArea

if TYPE_CHECKING:
    from textual.app import ComposeResult


class CustomTextArea(Container):
    """Standardized text area wrapper around Textual's TextArea widget.

    Provides consistent styling and integration with the TUI design system.
    A multi-line text input with optional syntax highlighting.

    CSS Classes: widget-custom-text-area

    Example:
        ```python
        text_area = CustomTextArea(
            placeholder="Enter text...",
            id="notes-input",
            language="python"
        )
        ```
    """

    CSS_PATH = "../../css/widgets/custom_text_area.tcss"

    def __init__(
        self,
        text: str = "",
        placeholder: str = "",
        *,
        id: str | None = None,
        classes: str = "",
        disabled: bool = False,
        language: str | None = None,
        show_line_numbers: bool = False,
        read_only: bool = False,
    ) -> None:
        """Initialize the custom text area wrapper.

        Args:
            text: Initial text content.
            placeholder: Placeholder text displayed when empty.
            id: Widget ID.
            classes: CSS classes (widget-custom-text-area is automatically added).
            disabled: Whether the text area is disabled.
            language: Syntax highlighting language (None for plain text).
            show_line_numbers: Whether to show line numbers.
            read_only: Whether the text area is read-only.
        """
        super().__init__(id=id, classes=f"widget-custom-text-area {classes}".strip())
        self._text = text
        self._placeholder = placeholder
        self._disabled = disabled
        self._language = language
        self._show_line_numbers = show_line_numbers
        self._read_only = read_only

    def compose(self) -> ComposeResult:
        """Compose the text area with Textual's TextArea widget."""
        yield TextualTextArea(
            text=self._text,
            placeholder=self._placeholder,
            disabled=self._disabled,
            language=self._language,
            show_line_numbers=self._show_line_numbers,
            read_only=self._read_only,
            id=self.id,
        )

    @property
    def text_area(self) -> TextualTextArea:
        """Get the underlying Textual TextArea widget.

        Returns:
            The composed Textual TextArea widget.
        """
        return self.query_one(TextualTextArea)

    @property
    def text(self) -> str:
        """Get the current text content.

        Returns:
            The text content.
        """
        return self.text_area.text

    @text.setter
    def text(self, val: str) -> None:
        """Set the text content.

        Args:
            val: New text content.
        """
        self.text_area.text = val

    @property
    def placeholder(self) -> str:
        """Get the placeholder text.

        Returns:
            The placeholder text.
        """
        return str(self.text_area.placeholder)

    @placeholder.setter
    def placeholder(self, val: str) -> None:
        """Set the placeholder text.

        Args:
            val: New placeholder text.
        """
        self.text_area.placeholder = val

    def clear(self) -> None:
        """Clear the text content."""
        self.text_area.clear()

    def select_all(self) -> None:
        """Select all text."""
        self.text_area.select_all()
