"""CustomMarkdown widget - standardized wrapper around Textual's Markdown/MarkdownViewer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.containers import Container
from textual.widgets import Markdown as TextualMarkdown

if TYPE_CHECKING:
    from textual.app import ComposeResult


class CustomMarkdown(Container):
    """Standardized markdown wrapper around Textual's Markdown widget.

    Provides consistent styling and integration with the TUI design system.
    Renders Markdown content for documentation display.

    CSS Classes: widget-custom-markdown

    Example:
        ```python
        markdown = CustomMarkdown(
            content="# Heading\n\nSome **bold** text.",
            id="readme-display"
        )
        ```
    """

    CSS_PATH = "../../css/widgets/custom_markdown.tcss"

    def __init__(
        self,
        content: str = "",
        *,
        id: str | None = None,
        classes: str = "",
    ) -> None:
        """Initialize the custom markdown wrapper.

        Args:
            content: Markdown content to render.
            id: Widget ID.
            classes: CSS classes (widget-custom-markdown is automatically added).
        """
        super().__init__(id=id, classes=f"widget-custom-markdown {classes}".strip())
        self._content = content

    def compose(self) -> ComposeResult:
        """Compose the markdown with Textual's Markdown widget."""
        yield TextualMarkdown(
            self._content,
            id=self.id,
        )

    @property
    def markdown(self) -> TextualMarkdown:
        """Get the underlying Textual Markdown widget.

        Returns:
            The composed Textual Markdown widget.
        """
        return self.query_one(TextualMarkdown)

    @property
    def content(self) -> str:
        """Get the current markdown content.

        Returns:
            The markdown content.
        """
        return self._content

    @content.setter
    def content(self, val: str) -> None:
        """Set the markdown content.

        Args:
            val: New markdown content.
        """
        self._content = val
        self.markdown.update(val)
