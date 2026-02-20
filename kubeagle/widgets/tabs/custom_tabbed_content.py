"""CustomTabbedContent widget - standardized direct extension of Textual's TabbedContent."""

from __future__ import annotations

from contextlib import suppress

from textual.css.query import NoMatches
from textual.widgets import TabbedContent as TextualTabbedContent
from textual.widgets._tabbed_content import ContentTabs


class CustomTabbedContent(TextualTabbedContent):
    """Standardized tabbed content extending Textual's TabbedContent widget.

    Provides consistent styling and integration with the TUI design system.
    Directly inherits from Textual's built-in TabbedContent widget so that
    the context-manager compose pattern works natively -- TabPanes yielded
    inside ``with CustomTabbedContent(...):`` become children of the
    TabbedContent itself, not of an intermediate Container.

    CSS Classes: widget-custom-tabbed-content

    Example:
        ```python
        # Using TabPane context manager pattern
        with CustomTabbedContent(id="main-tabs"):
            with TabPane("Tab 1", id="tab1"):
                yield SomeContent()
            with TabPane("Tab 2", id="tab2"):
                yield OtherContent()
        ```
    """

    CSS_PATH = "../../css/widgets/custom_tabbed_content.tcss"

    def __init__(
        self,
        *titles: str,
        id: str | None = None,
        classes: str = "",
        initial: str = "",
    ) -> None:
        """Initialize the custom tabbed content.

        Args:
            *titles: Tab titles (use TabPane context manager for content).
            id: Widget ID.
            classes: CSS classes (widget-custom-tabbed-content is automatically added).
            initial: ID of the initially active tab.
        """
        super().__init__(
            *titles,
            id=id,
            classes=f"widget-custom-tabbed-content {classes}".strip(),
            initial=initial or "",
        )

    def on_mount(self) -> None:
        """Constrain ContentTabs height so the content area gets remaining space."""
        with suppress(NoMatches):
            tabs = self.query_one(ContentTabs)
            tabs.styles.height = 3

    @property
    def _titles(self) -> tuple[str, ...]:
        """Backward-compatible accessor returning titles as a tuple of strings.

        Returns:
            Tuple of title strings.
        """
        return tuple(str(t) for t in self.titles)
