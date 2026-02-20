"""Generic table component for DataTable operations."""

from textual.css.query import QueryError
from textual.dom import DOMNode
from textual.widgets import DataTable


class GenericTableComponent:
    """Generic wrapper for DataTable operations.

    Replaces duplicate NodeTableComponent, TeamTableComponent, ChartsTableComponent.
    """

    def __init__(self, table_id: str = "data-table") -> None:
        """Initialize the table component.

        Args:
            table_id: ID for the DataTable widget.
        """
        self.table_id = table_id

    def get_table(self, parent: DOMNode) -> DataTable | None:
        """Get DataTable by ID from parent.

        Args:
            parent: Parent DOMNode to query from.

        Returns:
            DataTable widget or None if not found.
        """
        try:
            return parent.query_one(f"#{self.table_id}", DataTable)
        except QueryError:
            return None

    def update_table(self, parent: DOMNode, data: list, columns: list) -> None:
        """Update table with new data.

        Args:
            parent: Parent DOMNode.
            data: List of row data tuples.
            columns: List of column labels.
        """
        table = self.get_table(parent)
        if table is None:
            return

        table.clear()
        if not table.columns:
            for col in columns:
                table.add_column(col)
        for row in data:
            table.add_row(*row)

    def clear_table(self, parent: DOMNode) -> None:
        """Clear table data.

        Args:
            parent: Parent DOMNode.
        """
        table = self.get_table(parent)
        if table is not None:
            table.clear()
