"""CustomFilterBar widget combining search, filters, and stats.

Standard Reactive Pattern:
- Inherits from StatefulWidget
- Has is_loading, data, error reactives
- Implements watch_* methods

CSS Classes: widget-custom-filter-bar
"""

from collections.abc import Callable
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Static

from kubeagle.widgets._base import StatefulWidget
from kubeagle.widgets.filter.custom_filter_group import CustomFilterGroup
from kubeagle.widgets.filter.custom_search_bar import (
    CustomFilterButton,
    CustomSearchBar,
)


class CustomFilterStats(StatefulWidget):
    """Display for filtered result count.

    CSS Classes: widget-custom-filter-stats
    """

    CSS_PATH = "../../css/widgets/custom_filter_bar.tcss"
    _id_pattern = "custom-filter-stats-{uuid}"
    _default_classes = "widget-custom-filter-stats"

    # Standard reactive attributes
    is_loading = reactive(False)
    data = reactive[list[dict]]([])
    error = reactive[str | None](None)

    # Widget-specific reactives
    total = reactive(0, init=False)
    filtered = reactive[int | None](None, init=False)

    def __init__(
        self,
        total: int = 0,
        filtered: int | None = None,
        id: str | None = None,
        classes: str = "",
    ) -> None:
        """Initialize the custom filter stats.

        Args:
            total: Total item count.
            filtered: Filtered item count (None to show only total).
            id: Widget ID.
            classes: CSS classes.
        """
        super().__init__(id=id, classes=classes)
        self._total = total
        self._filtered = filtered

    def compose(self) -> ComposeResult:
        """Compose the filter stats widget."""
        yield Static(self._get_display_text(), classes="stats-text")

    def _get_display_text(self) -> str:
        """Get the display text for current state.

        Returns:
            The formatted display text.
        """
        if self._filtered is not None and self._filtered != self._total:
            return f"Showing {self._filtered} of {self._total}"
        return f"{self._total} items"

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

    def watch_total(self, new_total: int) -> None:
        """Watch for total changes.

        Args:
            new_total: The new total count.
        """
        self._total = new_total
        self.query_one(".stats-text", Static).update(self._get_display_text())

    def watch_filtered(self, new_filtered: int | None) -> None:
        """Watch for filtered changes.

        Args:
            new_filtered: The new filtered count.
        """
        self._filtered = new_filtered
        self.query_one(".stats-text", Static).update(self._get_display_text())

    def update(self, total: int, filtered: int | None = None) -> None:
        """Update the stats.

        Args:
            total: Total item count.
            filtered: Filtered item count.
        """
        self._total = total
        self._filtered = filtered
        self.total = total
        if filtered is not None:
            self.filtered = filtered


class CustomFilterBar(StatefulWidget):
    """Complete filter bar combining search, filters, and stats.

    CSS Classes: widget-custom-filter-bar
    """

    CSS_PATH = "../../css/widgets/custom_filter_bar.tcss"
    _id_pattern = "custom-filter-bar-{uuid}"
    _default_classes = "widget-custom-filter-bar"

    # Standard reactive attributes
    is_loading = reactive(False)
    data = reactive[list[dict]]([])
    error = reactive[str | None](None)

    def __init__(
        self,
        placeholder: str = "Search...",
        filter_options: list[str] | None = None,
        on_filter: Callable[[str, list[str]], None] | None = None,
        show_stats: bool = True,
        id: str | None = None,
        classes: str = "",
    ) -> None:
        """Initialize the custom filter bar.

        Args:
            placeholder: Search input placeholder.
            filter_options: List of filter options.
            on_filter: Callback when filters change.
            show_stats: Whether to show stats display.
            id: Widget ID.
            classes: CSS classes.
        """
        super().__init__(id=id, classes=classes)
        self._placeholder = placeholder
        self._filter_options = filter_options or []
        self._on_filter = on_filter
        self._show_stats = show_stats

    def compose(self) -> ComposeResult:
        """Compose the filter bar widgets."""
        with Horizontal(classes="filter-bar-container"):
            if self._filter_options:
                yield CustomFilterGroup(
                    label="",
                    options=self._filter_options,
                    on_change=self._notify_filter,
                    classes="filter-group",
                )
            yield CustomSearchBar(
                placeholder=self._placeholder,
                on_change=self._notify_filter,
                classes="search-bar",
            )
            if self._show_stats:
                yield CustomFilterStats(id="filter-stats", classes="filter-stats")
            yield CustomFilterButton("Clear", id="clear-filters-btn", classes="clear-filters-btn")

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

    def _notify_filter(self, *args: Any) -> None:
        """Notify parent of filter change."""
        search = self.query_one(".search-bar", CustomSearchBar).value
        if self._filter_options:
            group = self.query_one(".filter-group", CustomFilterGroup)
            active_filters = group.get_active()
        else:
            active_filters = []

        if self._on_filter:
            self._on_filter(search, active_filters)
