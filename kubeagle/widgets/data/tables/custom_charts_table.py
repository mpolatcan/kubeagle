"""CustomChartsTable widget for Helm charts data.

Standard Reactive Pattern:
- Inherits from CustomTableBase and DataTable
- Has is_loading, data, error reactives
- Implements watch_* methods

CSS Classes: widget-custom-charts-table
"""

from __future__ import annotations

from typing import Any, ClassVar

from textual.reactive import reactive
from textual.widgets import DataTable
from textual.widgets._data_table import RowKey

from kubeagle.widgets.data.tables.custom_table import CustomTableBase


class CustomChartsTable(CustomTableBase, DataTable):
    """Data table for displaying Helm charts.

    CSS Classes: widget-custom-charts-table
    """

    CSS_PATH = "../../../css/widgets/custom_charts_table.tcss"
    _id_pattern = "custom-charts-table-{uuid}"
    _default_classes = "widget-custom-charts-table"

    # Standard reactive attributes (inherited from mixin)
    is_loading = reactive(False)
    data = reactive[list[dict]]([])
    error = reactive[str | None](None)

    _COLUMN_DEFS: ClassVar[list[tuple[str, str]]] = [
        ("Name", "name"),
        ("Team", "team"),
        ("QoS", "qos_class"),
        ("Replicas", "replicas"),
        ("Liveness", "has_liveness"),
        ("Readiness", "has_readiness"),
    ]

    _NUMERIC_COLUMNS: ClassVar[set[str]] = {"replicas"}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the custom charts table."""
        super().__init__(*args, **kwargs)
        self._all_row_data: list[tuple[Any, ...]] = []

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

    def add_row(self, *args: Any, **kwargs: Any) -> RowKey:
        """Override add_row to store original row data."""
        self._all_row_data.append(args)
        return super().add_row(*args, **kwargs)

    def filter_by_team(self, team: str) -> None:
        """Filter rows by team name.

        Args:
            team: Team name to filter by. Empty string shows all rows.
        """
        self.clear()

        if not team:
            for row_data in self._all_row_data:
                super().add_row(*row_data)
            return

        for row_data in self._all_row_data:
            if len(row_data) > 1:
                row_team = str(row_data[1]).lower()
                if team.lower() in row_team:
                    super().add_row(*row_data)

    def sort_by_column(self, column_key: str, reverse: bool = False) -> None:
        """Sort table by column.

        Args:
            column_key: The column key to sort by.
            reverse: If True, sort in descending order.
        """
        self._sort_column = column_key
        self._sort_reverse = reverse
        self.sort(column_key, reverse=reverse)

    @property
    def all_row_data(self) -> list[tuple[Any, ...]]:
        """Get all stored row data.

        Returns:
            List of all row data tuples.
        """
        return self._all_row_data
