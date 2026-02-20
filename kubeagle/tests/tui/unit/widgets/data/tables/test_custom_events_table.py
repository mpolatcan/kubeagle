"""Tests for CustomEventsTable widget.

Tests cover:
- CustomEventsTable instantiation
- Event-specific column definitions
- Data handling
"""

from __future__ import annotations

import pytest

from kubeagle.widgets.data.tables.custom_events_table import (
    CustomEventsTable,
)

# =============================================================================
# CustomEventsTable Widget Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.fast
class TestCustomEventsTable:
    """Tests for CustomEventsTable widget."""

    def test_custom_events_table_instantiation(self) -> None:
        """Test CustomEventsTable can be instantiated."""
        table = CustomEventsTable()
        assert table is not None

    def test_custom_events_table_is_loading_reactive(self) -> None:
        """Test is_loading reactive attribute."""
        table = CustomEventsTable()
        assert hasattr(table, "is_loading")

    def test_custom_events_table_data_reactive(self) -> None:
        """Test data reactive attribute."""
        table = CustomEventsTable()
        assert hasattr(table, "data")

    def test_custom_events_table_error_reactive(self) -> None:
        """Test error reactive attribute."""
        table = CustomEventsTable()
        assert hasattr(table, "error")

    def test_custom_events_table_column_defs(self) -> None:
        """Test column definitions contain event columns."""
        table = CustomEventsTable()
        assert isinstance(table._COLUMN_DEFS, list)
        assert len(table._COLUMN_DEFS) > 0


@pytest.mark.unit
@pytest.mark.asyncio
class TestCustomEventsTableReactive:
    """Tests for CustomEventsTable reactive property changes."""

    async def test_watch_is_loading_does_not_raise(self) -> None:
        """Test watch_is_loading handles changes without error."""
        table = CustomEventsTable()
        table.watch_is_loading(True)
        table.watch_is_loading(False)

    async def test_watch_data_does_not_raise(self) -> None:
        """Test watch_data handles changes without error."""
        table = CustomEventsTable()
        test_data = [{"event": "test"}]
        table.watch_data(test_data)

    async def test_watch_error_handles_none(self) -> None:
        """Test watch_error handles None value."""
        table = CustomEventsTable()
        table.watch_error(None)

    async def test_watch_error_handles_message(self) -> None:
        """Test watch_error handles error message."""
        table = CustomEventsTable()
        table.watch_error("Event fetch failed")
