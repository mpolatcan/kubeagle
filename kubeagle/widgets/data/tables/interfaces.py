"""IDataProvider protocol for data table widgets."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class IDataProvider(ABC):
    """Protocol for data providers that feed data to CustomDataTable.

    This interface defines the contract for providing data to the
    CustomDataTable widget. Implementations should handle data fetching,
    filtering, and transformation.

    Example:
        ```python
        class ChartDataProvider(IDataProvider):
            def get_columns(self) -> list[tuple[str, str]]:
                return [("Name", "name"), ("Version", "version")]

            def get_rows(self) -> list[tuple[Any, ...]]:
                return [("nginx", "1.21.0"), ("redis", "6.2.0")]
        ```
    """

    @abstractmethod
    def get_columns(self) -> list[tuple[str, str]]:
        """Get column definitions for the table.

        Returns:
            List of (label, key) tuples defining columns.
        """
        ...

    @abstractmethod
    def get_rows(self) -> list[tuple[Any, ...]]:
        """Get row data for the table.

        Returns:
            List of tuples where each tuple is a row.
        """
        ...

    def filter_rows(self, column_key: str, value: str) -> list[tuple[Any, ...]]:
        """Filter rows by column value.

        Args:
            column_key: The column key to filter by.
            value: The value to match (partial match, case-insensitive).

        Returns:
            Filtered list of row tuples.
        """
        return self.get_rows()

    def sort_rows(
        self,
        rows: list[tuple[Any, ...]],
        column_key: str,
        reverse: bool = False,
    ) -> list[tuple[Any, ...]]:
        """Sort rows by column.

        Args:
            rows: List of rows to sort.
            column_key: The column key to sort by.
            reverse: If True, sort in descending order.

        Returns:
            Sorted list of row tuples.
        """
        return rows
