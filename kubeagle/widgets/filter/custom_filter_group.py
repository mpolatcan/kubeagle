"""CustomFilterGroup widget for collections of related filter chips.

Standard Reactive Pattern:
- Inherits from StatefulWidget
- Has is_loading, data, error reactives
- Implements watch_* methods

CSS Classes: widget-custom-filter-group
"""

from collections.abc import Callable

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Static

from kubeagle.widgets._base import StatefulWidget
from kubeagle.widgets.filter.custom_filter_chip import CustomFilterChip


class CustomFilterGroup(StatefulWidget):
    """Group of related filter chips.

    CSS Classes: widget-custom-filter-group
    """

    CSS_PATH = "../../css/widgets/custom_filter_group.tcss"
    DEFAULT_CSS = """
    CustomFilterGroup {
        layout: horizontal;
        height: auto;
        width: auto;
    }
    .group-label {
        width: auto;
        margin-right: 1;
    }
    .chips-container {
        width: auto;
        height: auto;
    }
    """
    _id_pattern = "custom-filter-group-{uuid}"
    _default_classes = "widget-custom-filter-group"

    # Standard reactive attributes
    is_loading = reactive(False)
    data = reactive[list[dict]]([])
    error = reactive[str | None](None)

    # Widget-specific reactives
    options = reactive[list[str]]([], init=False)
    selections = reactive[list[str]]([], init=False)

    def __init__(
        self,
        label: str,
        options: list[str],
        on_change: Callable[[str, bool], None] | None = None,
        multi_select: bool = False,
        id: str | None = None,
        classes: str = "",
    ) -> None:
        """Initialize the custom filter group.

        Args:
            label: Group label.
            options: List of option labels.
            on_change: Callback when selection changes.
            multi_select: Allow multiple selections.
            id: Widget ID.
            classes: CSS classes.
        """
        super().__init__(id=id, classes=classes)
        self._label = label
        self._options = options
        self._on_change = on_change
        self._multi_select = multi_select
        self._chips: dict[str, CustomFilterChip] = {}

    def compose(self) -> ComposeResult:
        """Compose the filter group widgets."""
        yield Static(self._label, classes="group-label")
        with Horizontal(classes="chips-container"):
            for option in self._options:
                chip = CustomFilterChip(
                    label=option,
                    on_toggle=lambda active, opt=option: self._on_chip_toggle(opt, active),
                )
                self._chips[option] = chip
                yield chip

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

    def watch_options(self, new_options: list[str]) -> None:
        """Watch for options changes.

        Args:
            new_options: The new options list.
        """
        self._options = new_options

    def watch_selections(self, selections: list[str]) -> None:
        """Watch for selections changes.

        Args:
            selections: The new selections list.
        """
        for option, chip in self._chips.items():
            chip.set_active(option in selections)

    def _on_chip_toggle(self, option: str, active: bool) -> None:
        """Handle chip toggle.

        Args:
            option: The option that was toggled.
            active: The new active state.
        """
        if not self._multi_select and active:
            for opt, chip in self._chips.items():
                if opt != option and chip.is_active:
                    chip.set_active(False)

        self.selections = self.get_active()

        if self._on_change:
            self._on_change(option, active)

    def get_active(self) -> list[str]:
        """Get list of active options.

        Returns:
            List of active option labels.
        """
        return [opt for opt, chip in self._chips.items() if chip.is_active]

    def set_active(self, options: list[str]) -> None:
        """Set active options.

        Args:
            options: List of options to activate.
        """
        self.selections = options

    @property
    def label(self) -> str:
        """Get the group label.

        Returns:
            The label text.
        """
        return self._label

    @property
    def multi_select(self) -> bool:
        """Check if multi-select is enabled.

        Returns:
            True if multi-select is enabled.
        """
        return self._multi_select
