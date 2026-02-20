"""CustomLink widget for the TUI application.

Standard Wrapper Pattern:
- Wraps Textual's Link with standardized styling
- Supports click to open URL
- Optional tooltip display

CSS Classes: widget-custom-link
"""

from __future__ import annotations

from textual.widgets import Link as TextualLink


class CustomLink(TextualLink):
    """Custom link widget with standardized styling.

    Wraps Textual's Link widget with consistent styling across the application.
    Displays clickable text that opens a URL when activated.

    CSS Classes: widget-custom-link

    Features:
        - Click or press Enter to open URL
        - Optional tooltip on hover
        - Focusable navigation
        - Disabled state support

    Example:
        >>> link = CustomLink(
        ...     "Visit Documentation",
        ...     url="https://docs.example.com",
        ...     tooltip="Open documentation"
        ... )
        >>> yield link
    """

    CSS_PATH = "../../css/widgets/custom_link.tcss"

    def __init__(
        self,
        text: str,
        url: str | None = None,
        tooltip: str | None = None,
        variant: str | None = None,
        id: str | None = None,
        classes: str = "",
        disabled: bool = False,
    ):
        """Initialize the custom link widget.

        Args:
            text: The text to display (required).
            url: The URL to open when clicked. If None, uses text as URL.
            tooltip: Optional tooltip text shown on hover.
            variant: Optional style variant (muted, success, warning, error).
            id: Widget ID.
            classes: CSS classes.
            disabled: Whether the link is disabled.
        """
        # Use text as URL if url is not provided
        final_url = url if url is not None else text

        super().__init__(
            text=text,
            url=final_url,
            tooltip=tooltip,
            id=id,
            classes=f"widget-custom-link {classes}".strip(),
            disabled=disabled,
        )

        # Add variant class if specified
        if variant:
            self.add_class(variant)

    @property
    def link_url(self) -> str:
        """Get the URL of the link.

        Returns:
            The URL to open when clicked.
        """
        return self.url

    @link_url.setter
    def link_url(self, value: str) -> None:
        """Set the URL of the link.

        Args:
            value: New URL to open when clicked.
        """
        self.url = value

    @property
    def link_text(self) -> str:
        """Get the text of the link.

        Returns:
            The display text.
        """
        return self.text

    @link_text.setter
    def link_text(self, value: str) -> None:
        """Set the text of the link.

        Args:
            value: New display text.
        """
        self.text = value
