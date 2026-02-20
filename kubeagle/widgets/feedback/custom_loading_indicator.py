"""CustomLoadingIndicator widget - standardized wrapper around Textual's LoadingIndicator."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.containers import Container
from textual.widgets import LoadingIndicator as TextualLoadingIndicator

if TYPE_CHECKING:
    from textual.app import ComposeResult


class CustomLoadingIndicator(Container):
    """Standardized loading indicator wrapper around Textual's LoadingIndicator widget.

    Provides consistent styling and integration with the TUI design system.
    Wraps Textual's built-in LoadingIndicator widget with standardized CSS classes.

    CSS Classes: widget-custom-loading-indicator

    Example:
        ```python
        CustomLoadingIndicator(
            classes="widget-custom-loading-indicator"
        )
    ```
    """

    CSS_PATH = "../../css/widgets/custom_loading_indicator.tcss"

    def __init__(
        self,
        id: str | None = None,
        classes: str = "",
        disabled: bool = False,
    ) -> None:
        """Initialize the custom loading indicator wrapper.

        Args:
            id: Widget ID.
            classes: CSS classes (widget-custom-loading-indicator is automatically added).
            disabled: Whether the loading indicator is disabled.
        """
        self._id = id
        self._inner_widget: TextualLoadingIndicator | None = None
        super().__init__(id=id, classes=f"widget-custom-loading-indicator {classes}".strip())
        self._disabled = disabled

    def compose(self) -> ComposeResult:
        """Compose the loading indicator with Textual's LoadingIndicator widget."""
        # Don't pass id to inner widget to avoid duplicate DOM IDs
        # The container has the ID, inner widget doesn't need its own
        indicator = TextualLoadingIndicator(
            disabled=self._disabled,
        )
        self._inner_widget = indicator
        yield indicator

    @property
    def loading_indicator(self) -> TextualLoadingIndicator | None:
        """Get the underlying Textual LoadingIndicator widget.

        Returns:
            The composed Textual LoadingIndicator widget or None if not yet mounted.
        """
        return self._inner_widget

    @property
    def disabled(self) -> bool:
        """Get the disabled state.

        Returns:
            True if disabled, False otherwise.
        """
        if self._inner_widget is not None:
            return self._inner_widget.disabled
        return self._disabled

    @disabled.setter
    def disabled(self, val: bool) -> None:
        """Set the disabled state.

        Args:
            val: New disabled state.
        """
        self._disabled = val
        if self._inner_widget is not None:
            self._inner_widget.disabled = val
