"""Data display widgets for the TUI application."""

from kubeagle.widgets.data.indicators import (
    CustomErrorRetryWidget,
    CustomLastUpdatedWidget,
    CustomStatusIndicator,
)
from kubeagle.widgets.data.kpi import CustomKPI
from kubeagle.widgets.data.tables import (
    CustomChartsTable,
    CustomColumnDef,
    CustomDataTable,
    CustomEventsTable,
    CustomNodeTable,
    CustomTableBase,
    CustomTableBuilder,
    CustomTableMixin,
    CustomViolationsTable,
)

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
    "CustomKPI",
    "CustomStatusIndicator",
    "CustomErrorRetryWidget",
    "CustomLastUpdatedWidget",
]
