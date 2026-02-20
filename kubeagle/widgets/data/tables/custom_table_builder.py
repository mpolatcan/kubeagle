"""Custom table builder utility for creating DataTable instances.

Standard Reactive Pattern:
- Builder pattern for creating consistent DataTable instances

CSS Classes: widget-custom-table
"""

from textual.widgets import DataTable

from kubeagle.models.types.columns import ColumnDef


class CustomTableBuilder:
    """Builder for creating DataTable instances with columns."""

    def __init__(self, id: str | None = None):
        """Initialize the table builder.

        Args:
            id: Optional widget ID.
        """
        self._id = id
        self._columns: list[ColumnDef] = []
        self._rows: list[tuple] = []
        self._classes: str = "widget-custom-table"

    def add_column(
        self,
        label: str,
        key: str,
        formatter=None,
        numeric: bool = False,
    ) -> "CustomTableBuilder":
        """Add a column definition.

        Args:
            label: Column label.
            key: Column key.
            formatter: Optional value formatter.
            numeric: Whether column contains numeric values.

        Returns:
            Self for chaining.
        """
        self._columns.append(ColumnDef(label, key, formatter, numeric))
        return self

    def add_row(self, *values) -> "CustomTableBuilder":
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
        table = DataTable(id=self._id, classes=self._classes)
        for col in self._columns:
            table.add_column(col.label, key=col.key)
        for row in self._rows:
            table.add_row(*row)
        return table


# Backward compatibility alias
CustomColumnDef = ColumnDef
