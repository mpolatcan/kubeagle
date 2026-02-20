"""CustomMarkdownViewer widget - standardized wrapper around Textual's MarkdownViewer."""

from __future__ import annotations

from textual.widgets import MarkdownViewer as TextualMarkdownViewer


class CustomMarkdownViewer(TextualMarkdownViewer):
    """Standardized markdown viewer with shared styling hooks."""

    CSS_PATH = "../../css/widgets/custom_markdown_viewer.tcss"

    def __init__(
        self,
        *args,
        classes: str = "",
        **kwargs,
    ) -> None:
        merged_classes = f"widget-custom-markdown-viewer {classes}".strip()
        super().__init__(*args, classes=merged_classes, **kwargs)
