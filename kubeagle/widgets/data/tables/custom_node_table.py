"""CustomNodeTable widget for cluster nodes data.

Standard Reactive Pattern:
- Inherits from CustomTableBase and DataTable
- Has is_loading, data, error reactives
- Implements watch_* methods

CSS Classes: widget-custom-node-table
"""

from __future__ import annotations

from typing import ClassVar

from textual.reactive import reactive
from textual.widgets import DataTable

from kubeagle.widgets.data.tables.custom_table import CustomTableBase


class CustomNodeTable(CustomTableBase, DataTable):
    """Data table for displaying cluster nodes.

    CSS Classes: widget-custom-node-table
    """

    CSS_PATH = "../../../css/widgets/custom_node_table.tcss"
    _id_pattern = "custom-node-table-{uuid}"
    _default_classes = "widget-custom-node-table"

    # Standard reactive attributes (inherited from mixin)
    is_loading = reactive(False)
    data = reactive[list[dict]]([])
    error = reactive[str | None](None)

    _COLUMN_DEFS: ClassVar[list[tuple[str, str]]] = [
        ("Name", "name"),
        ("Status", "status"),
        ("Node Group", "node_group"),
        ("Instance", "instance_type"),
        ("AZ", "availability_zone"),
        ("Pods", "pod_count"),
    ]

    _NUMERIC_COLUMNS: ClassVar[set[str]] = {"pod_count"}

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
