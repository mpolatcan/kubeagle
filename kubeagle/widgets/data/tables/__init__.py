"""Data table widgets for the TUI application."""

from kubeagle.widgets.data.tables.custom_charts_table import (
    CustomChartsTable,
)
from kubeagle.widgets.data.tables.custom_data_table import CustomDataTable
from kubeagle.widgets.data.tables.custom_events_table import (
    CustomEventsTable,
)
from kubeagle.widgets.data.tables.custom_node_table import CustomNodeTable
from kubeagle.widgets.data.tables.custom_table import (
    CustomTableBase,
    CustomTableMixin,
)
from kubeagle.widgets.data.tables.custom_table_builder import (
    CustomColumnDef,
    CustomTableBuilder,
)
from kubeagle.widgets.data.tables.custom_violations_table import (
    CustomViolationsTable,
)
from kubeagle.widgets.data.tables.interfaces import IDataProvider

__all__ = [
    "CustomTableBase",
    "CustomTableMixin",
    "CustomDataTable",
    "CustomNodeTable",
    "CustomChartsTable",
    "CustomEventsTable",
    "CustomViolationsTable",
    "CustomColumnDef",
    "CustomTableBuilder",
    "IDataProvider",
]
