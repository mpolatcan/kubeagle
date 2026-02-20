"""Pod list component for cluster screen.

Note: This component is unused dead code retained for backward compatibility
with existing test imports.  It may be removed in a future cleanup once the
corresponding test fixtures are updated.
"""

from __future__ import annotations

from textual.css.query import QueryError
from textual.dom import DOMNode

from kubeagle.widgets import CustomDataTable


class PodListComponent:
    """Component for displaying pod data in a DataTable."""

    def __init__(self, table_id: str = "pods-table") -> None:
        """Initialize pod list component.

        Args:
            table_id: ID for the DataTable widget
        """
        self.table_id = table_id

    def get_table(self, parent: DOMNode) -> CustomDataTable | None:
        """Get the DataTable widget.

        Args:
            parent: Parent DOMNode to query from

        Returns:
            DataTable widget or None if not found.
        """
        try:
            return parent.query_one(f"#{self.table_id}", CustomDataTable)
        except QueryError:
            return None

    def update_table(self, parent: DOMNode, _pods: list) -> None:
        """Update the table with pod data.

        Args:
            parent: Parent DOMNode
            _pods: List of pod data
        """
        table = self.get_table(parent)
        if table is None:
            return
        # Implementation would populate the table with pod data
