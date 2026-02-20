"""CustomStatic widget for the TUI application.

Standard Wrapper Pattern:
- Wraps Textual's Static with standardized styling
- Supports alignment: left, center, right, justify
- Optional styling variants for emphasis

CSS Classes: widget-custom-static
"""

from __future__ import annotations

from textual.widgets import Static as TextualStatic


class CustomStatic(TextualStatic):
    """Custom static text widget with standardized styling.

    Wraps Textual's Static with consistent styling across the application.
    Supports various alignment options and emphasis variants.

    CSS Classes: widget-custom-static

    Alignment:
        - left: Left-aligned text (default)
        - center: Center-aligned text
        - right: Right-aligned text
        - justify: Justified text

    Example:
        >>> static = CustomStatic("Hello, World!")
        >>> yield static
    """

    CSS_PATH = "../../css/widgets/custom_static.tcss"

    def __init__(
        self,
        content: str = "",
        align: str = "left",
        emphasis: str | None = None,
        markup: bool = True,
        id: str | None = None,
        classes: str = "",
    ):
        """Initialize the custom static widget.

        Args:
            content: Text content to display.
            align: Text alignment (left, center, right, justify).
            emphasis: Optional emphasis style (muted, accent, success, warning, error, bold, italic, underline, highlight, code).
            markup: Whether to parse Rich markup in the content. Set to False for dynamic/user content.
            id: Widget ID.
            classes: CSS classes.
        """
        merged_classes = f"widget-custom-static {classes}".strip()
        super().__init__(content, markup=markup, id=id, classes=merged_classes)

        # Build alignment class (only if not left, since left is default)
        if align != "left":
            self.add_class(f"align-{align}")

        # Add emphasis class if specified
        if emphasis:
            self.add_class(emphasis)
