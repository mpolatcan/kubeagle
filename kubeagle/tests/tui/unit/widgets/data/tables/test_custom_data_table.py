"""Tests for CustomDataTable widget.

Tests cover:
- CustomDataTable instantiation
- Reactive property changes
- Data handling and rendering
- Column definitions
"""

from __future__ import annotations

import pytest

from kubeagle.widgets.data.tables.custom_data_table import CustomDataTable

# =============================================================================
# CustomDataTable Widget Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.fast
class TestCustomDataTable:
    """Tests for CustomDataTable widget."""

    def test_custom_data_table_instantiation(self) -> None:
        """Test CustomDataTable can be instantiated."""
        table = CustomDataTable()
        assert table is not None

    def test_custom_data_table_is_loading_reactive(self) -> None:
        """Test is_loading reactive attribute."""
        table = CustomDataTable()
        assert hasattr(table, "is_loading")

    def test_custom_data_table_data_reactive(self) -> None:
        """Test data reactive attribute."""
        table = CustomDataTable()
        assert hasattr(table, "data")

    def test_custom_data_table_error_reactive(self) -> None:
        """Test error reactive attribute."""
        table = CustomDataTable()
        assert hasattr(table, "error")

    def test_custom_data_table_column_defs(self) -> None:
        """Test column definitions are defined."""
        table = CustomDataTable()
        assert hasattr(table, "_COLUMN_DEFS")
        assert isinstance(table._COLUMN_DEFS, list)

    def test_custom_data_table_numeric_columns(self) -> None:
        """Test numeric columns set is defined."""
        table = CustomDataTable()
        assert hasattr(table, "_NUMERIC_COLUMNS")
        assert isinstance(table._NUMERIC_COLUMNS, set)


@pytest.mark.unit
@pytest.mark.asyncio
class TestCustomDataTableReactive:
    """Tests for CustomDataTable reactive property changes."""

    async def test_watch_is_loading_does_not_raise(self) -> None:
        """Test watch_is_loading handles changes without error."""
        table = CustomDataTable()
        table.watch_is_loading(True)
        table.watch_is_loading(False)

    async def test_watch_data_does_not_raise(self) -> None:
        """Test watch_data handles changes without error."""
        table = CustomDataTable()
        test_data = [{"key": "value"}]
        table.watch_data(test_data)

    async def test_watch_error_handles_none(self) -> None:
        """Test watch_error handles None value."""
        table = CustomDataTable()
        table.watch_error(None)

    async def test_watch_error_handles_message(self) -> None:
        """Test watch_error handles error message."""
        table = CustomDataTable()
        table.watch_error("Error occurred")
