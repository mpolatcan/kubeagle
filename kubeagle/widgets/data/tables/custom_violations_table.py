"""CustomViolationsTable widget for optimization violations data.

Standard Reactive Pattern:
- Inherits from CustomTableBase and DataTable
- Has is_loading, data, error reactives
- Implements watch_* methods
- Enter key selection support

CSS Classes: widget-custom-violations-table
"""

from __future__ import annotations

from typing import ClassVar

from textual.reactive import reactive
from textual.widgets import DataTable

from kubeagle.widgets.data.tables.custom_table import CustomTableBase


class CustomViolationsTable(CustomTableBase, DataTable):
    """Data table for displaying optimization violations.

    CSS Classes: widget-custom-violations-table
    """

    CSS_PATH = "../../../css/widgets/custom_violations_table.tcss"
    _id_pattern = "custom-violations-table-{uuid}"
    _default_classes = "widget-custom-violations-table"

    # Standard reactive attributes (inherited from mixin)
    is_loading = reactive(False)
    data = reactive[list[dict]]([])
    error = reactive[str | None](None)

    _COLUMN_DEFS: ClassVar[list[tuple[str, str]]] = [
        ("Severity", "severity"),
        ("Chart", "chart_name"),
        ("Rule", "rule_name"),
        ("Description", "description"),
    ]

    _NUMERIC_COLUMNS: ClassVar[set[str]] = set()

    BINDINGS = [
        ("enter", "select_row", "Select Row"),
    ]

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

    def action_select_row(self) -> None:
        """Trigger row selection when Enter is pressed."""
        cursor_row = self.cursor_row
        row_count = self.row_count
        if cursor_row is not None and 0 <= cursor_row < row_count:
            row_key, _ = self.coordinate_to_cell_key(self.cursor_coordinate)
            self.post_message(DataTable.RowSelected(self, cursor_row, row_key))
