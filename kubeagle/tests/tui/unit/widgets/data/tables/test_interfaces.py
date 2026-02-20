"""Unit tests for IDataProvider interface in widgets/data/tables/interfaces.py.

Tests cover:
- IDataProvider is abstract (cannot be instantiated directly)
- Abstract methods get_columns and get_rows
- Default implementations for filter_rows and sort_rows
- Concrete implementation pattern
"""

from __future__ import annotations

from abc import ABC
from typing import Any

import pytest

from kubeagle.widgets.data.tables.interfaces import IDataProvider

# =============================================================================
# IDataProvider ABC tests
# =============================================================================


class TestIDataProviderABC:
    """Test IDataProvider abstract base class."""

    def test_is_abstract(self) -> None:
        assert issubclass(IDataProvider, ABC)

    def test_cannot_instantiate_directly(self) -> None:
        with pytest.raises(TypeError):
            IDataProvider()

    def test_has_get_columns_method(self) -> None:
        assert hasattr(IDataProvider, "get_columns")

    def test_has_get_rows_method(self) -> None:
        assert hasattr(IDataProvider, "get_rows")

    def test_has_filter_rows_method(self) -> None:
        assert hasattr(IDataProvider, "filter_rows")

    def test_has_sort_rows_method(self) -> None:
        assert hasattr(IDataProvider, "sort_rows")


# =============================================================================
# Concrete implementation for testing
# =============================================================================


class MockDataProvider(IDataProvider):
    """Concrete mock implementation for testing."""

    def __init__(self) -> None:
        self._columns = [("Name", "name"), ("Version", "version")]
        self._rows = [("nginx", "1.21.0"), ("redis", "6.2.0"), ("postgres", "14.0")]

    def get_columns(self) -> list[tuple[str, str]]:
        return self._columns

    def get_rows(self) -> list[tuple[Any, ...]]:
        return self._rows


# =============================================================================
# Concrete implementation tests
# =============================================================================


class TestConcreteDataProvider:
    """Test IDataProvider with a concrete implementation."""

    def test_can_instantiate_concrete(self) -> None:
        provider = MockDataProvider()
        assert provider is not None

    def test_get_columns_returns_list(self) -> None:
        provider = MockDataProvider()
        columns = provider.get_columns()
        assert isinstance(columns, list)

    def test_get_columns_format(self) -> None:
        provider = MockDataProvider()
        columns = provider.get_columns()
        for col in columns:
            assert isinstance(col, tuple)
            assert len(col) == 2
            assert isinstance(col[0], str)  # label
            assert isinstance(col[1], str)  # key

    def test_get_rows_returns_list(self) -> None:
        provider = MockDataProvider()
        rows = provider.get_rows()
        assert isinstance(rows, list)

    def test_get_rows_format(self) -> None:
        provider = MockDataProvider()
        rows = provider.get_rows()
        for row in rows:
            assert isinstance(row, tuple)

    def test_get_rows_count(self) -> None:
        provider = MockDataProvider()
        rows = provider.get_rows()
        assert len(rows) == 3


# =============================================================================
# Default filter_rows
# =============================================================================


class TestDefaultFilterRows:
    """Test default filter_rows implementation."""

    def test_filter_rows_returns_all_rows_by_default(self) -> None:
        provider = MockDataProvider()
        filtered = provider.filter_rows("name", "nginx")
        # Default implementation returns all rows (no filtering)
        assert len(filtered) == 3

    def test_filter_rows_returns_list(self) -> None:
        provider = MockDataProvider()
        result = provider.filter_rows("name", "test")
        assert isinstance(result, list)


# =============================================================================
# Default sort_rows
# =============================================================================


class TestDefaultSortRows:
    """Test default sort_rows implementation."""

    def test_sort_rows_returns_same_rows(self) -> None:
        provider = MockDataProvider()
        rows = provider.get_rows()
        sorted_rows = provider.sort_rows(rows, "name")
        # Default implementation returns rows unchanged
        assert sorted_rows == rows

    def test_sort_rows_with_reverse(self) -> None:
        provider = MockDataProvider()
        rows = provider.get_rows()
        sorted_rows = provider.sort_rows(rows, "name", reverse=True)
        # Default implementation returns rows unchanged even with reverse
        assert sorted_rows == rows

    def test_sort_rows_returns_list(self) -> None:
        provider = MockDataProvider()
        rows = provider.get_rows()
        result = provider.sort_rows(rows, "name")
        assert isinstance(result, list)
