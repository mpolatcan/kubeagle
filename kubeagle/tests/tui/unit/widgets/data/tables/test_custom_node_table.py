"""Tests for CustomNodeTable widget.

Tests cover:
- CustomNodeTable instantiation
- Node-specific column definitions
- Data handling
"""

from __future__ import annotations

import pytest

from kubeagle.widgets.data.tables.custom_node_table import CustomNodeTable

# =============================================================================
# CustomNodeTable Widget Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.fast
class TestCustomNodeTable:
    """Tests for CustomNodeTable widget."""

    def test_custom_node_table_instantiation(self) -> None:
        """Test CustomNodeTable can be instantiated."""
        table = CustomNodeTable()
        assert table is not None

    def test_custom_node_table_is_loading_reactive(self) -> None:
        """Test is_loading reactive attribute."""
        table = CustomNodeTable()
        assert hasattr(table, "is_loading")

    def test_custom_node_table_data_reactive(self) -> None:
        """Test data reactive attribute."""
        table = CustomNodeTable()
        assert hasattr(table, "data")

    def test_custom_node_table_error_reactive(self) -> None:
        """Test error reactive attribute."""
        table = CustomNodeTable()
        assert hasattr(table, "error")

    def test_custom_node_table_column_defs(self) -> None:
        """Test column definitions contain node columns."""
        table = CustomNodeTable()
        assert isinstance(table._COLUMN_DEFS, list)
        assert len(table._COLUMN_DEFS) > 0


@pytest.mark.unit
@pytest.mark.asyncio
class TestCustomNodeTableReactive:
    """Tests for CustomNodeTable reactive property changes."""

    async def test_watch_is_loading_does_not_raise(self) -> None:
        """Test watch_is_loading handles changes without error."""
        table = CustomNodeTable()
        table.watch_is_loading(True)
        table.watch_is_loading(False)

    async def test_watch_data_does_not_raise(self) -> None:
        """Test watch_data handles changes without error."""
        table = CustomNodeTable()
        test_data = [{"node": "test"}]
        table.watch_data(test_data)

    async def test_watch_error_handles_none(self) -> None:
        """Test watch_error handles None value."""
        table = CustomNodeTable()
        table.watch_error(None)

    async def test_watch_error_handles_message(self) -> None:
        """Test watch_error handles error message."""
        table = CustomNodeTable()
        table.watch_error("Node fetch failed")
