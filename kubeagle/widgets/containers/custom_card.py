"""CustomCard container widget for the TUI application.

Standard Wrapper Pattern:
- Inherits from Container
- Presentational widget with title support
- Wraps Static widgets for content display

CSS Classes: widget-custom-card
"""

from __future__ import annotations

from contextlib import suppress

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static


class CustomCard(Container):
    """Custom card container for displaying grouped content.

    A presentational widget that displays a title and content area.
    Uses Container base class for standardized wrapper pattern.

    CSS Classes: widget-custom-card

    Example:
        >>> card = CustomCard(title="Statistics")
        >>> yield card
    """

    CSS_PATH = "../../css/widgets/custom_card.tcss"

    def __init__(self, title: str = "", id: str | None = None, classes: str = ""):
        """Initialize the custom card.

        Args:
            title: Optional card title.
            id: Widget ID.
            classes: CSS classes.
        """
        super().__init__(id=id, classes=f"widget-custom-card {classes}".strip())
        self._title = title

    def compose(self) -> ComposeResult:
        """Compose the custom card widgets."""
        if self._title:
            yield Static(self._title, classes="card-title")
        yield Static("", classes="card-content")

    def set_title(self, title: str) -> None:
        """Set the card title.

        Args:
            title: The new title text.
        """
        self._title = title
        with suppress(Exception):
            title_widget = self.query_one(".card-title", Static)
            title_widget.update(title)

    @property
    def card_title(self) -> str:
        """Get the card title.

        Returns:
            The title text.
        """
        return self._title
