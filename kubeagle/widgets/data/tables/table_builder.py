"""Data table builder utility."""

from typing import Any

from textual.widgets import DataTable

from kubeagle.models.types.columns import ColumnDef


class DataTableBuilder:
    """Builder for creating DataTable instances with columns."""

    def __init__(self, id: str | None = None):
        self._id = id
        self._columns: list[ColumnDef] = []
        self._rows: list[tuple[Any, ...]] = []

    def add_column(self, column: ColumnDef) -> "DataTableBuilder":
        """Add a column definition.

        Args:
            column: The column definition to add.

        Returns:
            Self for chaining.
        """
        self._columns.append(column)
        return self

    def add_row(self, *values: Any) -> "DataTableBuilder":
        """Add a row of data.

        Args:
            *values: Row values corresponding to column order.

        Returns:
            Self for chaining.
        """
        self._rows.append(values)
        return self

    def build(self) -> DataTable:
        """Build the DataTable widget.

        Returns:
            Configured DataTable instance.
        """
        table = DataTable(id=self._id)
        for col in self._columns:
            table.add_column(col.label, key=col.key)
        for row in self._rows:
            table.add_row(*row)
        return table
