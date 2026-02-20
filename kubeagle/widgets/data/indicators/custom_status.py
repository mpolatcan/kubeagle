"""Status indicator widgets for health status display.

Standard Wrapper Pattern:
- Inherits from Container
- Presentational widgets for status display

CSS Classes: widget-custom-status-indicator, widget-custom-error-retry,
widget-custom-last-updated
"""

from __future__ import annotations

from contextlib import suppress

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Static

from kubeagle.widgets.feedback.custom_button import CustomButton


class CustomStatusIndicator(Container):
    """Health status indicator with color coding.

    A presentational widget that displays a status indicator with
    color-coded dot and optional label.

    CSS Classes: widget-custom-status-indicator

    Example:
        >>> status = CustomStatusIndicator(status="success", label="Healthy")
        >>> yield status
    """

    CSS_PATH = "../../../css/widgets/custom_status.tcss"

    def __init__(
        self,
        status: str = "success",
        label: str = "",
        *,
        id: str | None = None,
        classes: str = "",
    ):
        """Initialize the custom status indicator.

        Args:
            status: Status level (success, warning, error, info).
            label: Optional label text.
            id: Widget ID.
            classes: CSS classes (widget-custom-status-indicator is automatically
                added).
        """
        super().__init__(
            id=id,
            classes=f"widget-custom-status-indicator {classes}".strip(),
        )
        self._status = status
        self._label = label

    def compose(self) -> ComposeResult:
        """Compose the status indicator."""
        yield Static("●", classes=f"status-dot {self._status}")
        if self._label:
            yield Static(self._label, classes="status-label")

    def set_status(self, status: str) -> None:
        """Set the status level.

        Args:
            status: The new status level.
        """
        self._status = status
        try:
            dot = self.query_one(".status-dot", Static)
            dot.update("●")
            dot.remove_class("success", "warning", "error", "info")
            dot.add_class(status)
        except Exception:
            pass

    @property
    def status(self) -> str:
        """Get the current status.

        Returns:
            The status level.
        """
        return self._status


class CustomErrorRetryWidget(Container):
    """Error message widget with retry button.

    A presentational widget that displays an error message with
    a retry button for recovery actions.

    CSS Classes: widget-custom-error-retry

    Example:
        >>> error_widget = CustomErrorRetryWidget(error_message="Connection failed")
        >>> yield error_widget
    """

    CSS_PATH = "../../../css/widgets/custom_status.tcss"

    BINDINGS = [
        ("enter", "retry", "Retry"),
        ("r", "retry", "Retry"),
    ]

    def __init__(
        self,
        error_message: str = "An error occurred",
        id: str | None = None,
        classes: str = "",
    ):
        """Initialize the custom error retry widget.

        Args:
            error_message: The error message to display.
            id: Widget ID.
            classes: CSS classes (widget-custom-error-retry is automatically
                added).
        """
        super().__init__(
            id=id,
            classes=f"widget-custom-error-retry {classes}".strip(),
        )
        self._error_message = error_message

    def compose(self) -> ComposeResult:
        """Compose the error retry widget."""
        with Vertical(classes="error-retry-container"):
            yield Static("ERROR: ", classes="error-icon")
            yield Static(self._error_message, classes="error-message")
            yield CustomButton("Retry", id="tab-retry-btn", classes="error-retry-btn")

    def action_retry(self) -> None:
        """Handle retry action - triggers button press."""
        with suppress(Exception):
            self.query_one("#tab-retry-btn", CustomButton).press()

    def set_error(self, message: str) -> None:
        """Update error message.

        Args:
            message: The new error message.
        """
        self._error_message = message
        with suppress(Exception):
            self.query_one(".error-message", Static).update(message)


class CustomLastUpdatedWidget(Container):
    """Widget displaying last updated timestamp.

    A presentational widget that shows when data was last updated.

    CSS Classes: widget-custom-last-updated

    Example:
        >>> updated = CustomLastUpdatedWidget(timestamp="2024-01-15 10:30")
        >>> yield updated
    """

    CSS_PATH = "../../../css/widgets/custom_status.tcss"

    def __init__(
        self,
        timestamp: str | None = None,
        *,
        id: str | None = None,
        classes: str = "",
    ):
        """Initialize the custom last updated widget.

        Args:
            timestamp: Initial timestamp string.
            id: Widget ID.
            classes: CSS classes (widget-custom-last-updated is automatically
                added).
        """
        super().__init__(
            id=id,
            classes=f"widget-custom-last-updated {classes}".strip(),
        )
        self._timestamp = timestamp or "Not yet loaded"

    def compose(self) -> ComposeResult:
        """Compose the last updated widget."""
        yield Static(self._get_display_text(), classes="last-updated-text")

    def _get_display_text(self) -> str:
        """Get the display text for current state.

        Returns:
            The formatted display text.
        """
        if self._timestamp:
            return f"Last updated: {self._timestamp}"
        return "Not yet loaded"

    def update(self, timestamp: str) -> None:
        """Update the timestamp display.

        Args:
            timestamp: The new timestamp string.
        """
        self._timestamp = timestamp
        with suppress(Exception):
            self.query_one(".last-updated-text", Static).update(
                self._get_display_text()
            )
