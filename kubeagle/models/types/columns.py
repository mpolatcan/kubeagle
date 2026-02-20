"""Column definition types for DataTables.

Consolidated from:
- widgets/data/tables/table_builder.py
- widgets/data/tables/custom_table_builder.py
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class ColumnDef:
    """Definition for a DataTable column.

    Attributes:
        label: Column header label.
        key: Unique key for the column.
        formatter: Optional callable to format cell values.
        numeric: Whether the column contains numeric values.
    """

    label: str
    key: str
    formatter: Callable[[Any], str] | None = None
    numeric: bool = False
