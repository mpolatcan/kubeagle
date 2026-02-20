"""CustomFilterChip widget for toggleable filter options.

Standard Reactive Pattern:
- Inherits from StatefulWidget
- Has is_loading, data, error reactives
- Implements watch_* methods
- Uses active reactive for chip state

CSS Classes: widget-custom-filter-chip
"""

from collections.abc import Callable

from textual.app import ComposeResult
from textual.events import Click
from textual.reactive import reactive
from textual.widgets import Static

from kubeagle.widgets._base import StatefulWidget


class CustomFilterChip(StatefulWidget):
    """Toggleable filter chip for boolean-style filters.

    CSS Classes: widget-custom-filter-chip
    """

    CSS_PATH = "../../css/widgets/custom_filter_chip.tcss"
    DEFAULT_CSS = """
    CustomFilterChip {
        layout: horizontal;
        height: auto;
        width: auto;
    }
    .chip-label {
        width: auto;
    }
    .chip-indicator {
        width: auto;
        margin-left: 1;
    }
    """
    _id_pattern = "custom-filter-chip-{uuid}"
    _default_classes = "widget-custom-filter-chip"

    # Standard reactive attributes
    is_loading = reactive(False)
    data = reactive[list[dict]]([])
    error = reactive[str | None](None)

    # Widget-specific reactive for active state
    active = reactive(False, init=False)

    def __init__(
        self,
        label: str,
        active: bool = False,
        on_toggle: Callable[[bool], None] | None = None,
        id: str | None = None,
        classes: str = "",
    ) -> None:
        """Initialize the custom filter chip.

        Args:
            label: Label text for the chip.
            active: Initial active state.
            on_toggle: Callback when state changes.
            id: Widget ID.
            classes: CSS classes.
        """
        super().__init__(id=id, classes=classes)
        self._label = label
        self._on_toggle = on_toggle
        self.set_reactive(CustomFilterChip.active, active)

    def compose(self) -> ComposeResult:
        """Compose the filter chip widgets."""
        yield Static(self._label, classes="chip-label")
        yield Static("*" if self.active else "o", classes="chip-indicator")

    def on_mount(self) -> None:
        """Apply the initial visual state after child widgets mount."""
        self._update_active_state(self.active)

    def watch_is_loading(self, loading: bool) -> None:
        """Update UI based on loading state.

        Args:
            loading: The new loading state.
        """
        pass

    def watch_data(self, data: list[dict]) -> None:
        """Update UI when data changes.

        Args:
            data: The new data value.
        """
        pass

    def watch_error(self, error: str | None) -> None:
        """Handle error state changes.

        Args:
            error: The error message or None if cleared.
        """
        pass

    def watch_active(self, active: bool) -> None:
        """Watch for active state changes.

        Args:
            active: The new active state.
        """
        self._update_active_state(active)
        if self._on_toggle:
            self._on_toggle(active)

    def _update_active_state(self, active: bool) -> None:
        """Update the UI for active state.

        Args:
            active: The active state.
        """
        indicator = self.query_one(".chip-indicator", Static)
        indicator.update("*" if active else "o")

        if active:
            self.add_css_class("active")
        else:
            self.remove_css_class("active")

    def on_click(self, event: Click) -> None:
        """Toggle chip on click."""
        self.toggle()

    def toggle(self) -> None:
        """Toggle the chip state."""
        self.active = not self.active

    def set_active(self, active: bool) -> None:
        """Set the active state.

        Args:
            active: New active state.
        """
        self.active = active

    @property
    def is_active(self) -> bool:
        """Check if chip is active.

        Returns:
            The active state.
        """
        return self.active

    @property
    def label(self) -> str:
        """Get the chip label.

        Returns:
            The label text.
        """
        return self._label
