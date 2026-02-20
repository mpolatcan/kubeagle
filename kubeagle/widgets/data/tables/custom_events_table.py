"""CustomEventsTable widget for cluster events data.

Standard Reactive Pattern:
- Inherits from CustomTableBase and DataTable
- Has is_loading, data, error reactives
- Implements watch_* methods

CSS Classes: widget-custom-events-table
"""

from __future__ import annotations

from typing import ClassVar

from textual.reactive import reactive
from textual.widgets import DataTable

from kubeagle.widgets.data.tables.custom_table import CustomTableBase


class CustomEventsTable(CustomTableBase, DataTable):
    """Data table for displaying cluster events.

    CSS Classes: widget-custom-events-table
    """

    CSS_PATH = "../../../css/widgets/custom_events_table.tcss"
    _id_pattern = "custom-events-table-{uuid}"
    _default_classes = "widget-custom-events-table"

    # Standard reactive attributes (inherited from mixin)
    is_loading = reactive(False)
    data = reactive[list[dict]]([])
    error = reactive[str | None](None)

    _COLUMN_DEFS: ClassVar[list[tuple[str, str]]] = [
        ("Type", "type"),
        ("Reason", "reason"),
        ("Message", "message"),
        ("Count", "count"),
    ]

    _NUMERIC_COLUMNS: ClassVar[set[str]] = {"count"}

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
        self.refresh()

    def watch_error(self, error: str | None) -> None:
        """Handle error state changes.

        Args:
            error: The error message or None if cleared.
        """
        pass
