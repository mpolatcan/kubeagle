"""Tests for CustomViolationsTable widget.

Tests cover:
- CustomViolationsTable instantiation
- Violation-specific column definitions
- Data handling
"""

from __future__ import annotations

import pytest

from kubeagle.widgets.data.tables.custom_violations_table import (
    CustomViolationsTable,
)

# =============================================================================
# CustomViolationsTable Widget Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.fast
class TestCustomViolationsTable:
    """Tests for CustomViolationsTable widget."""

    def test_custom_violations_table_instantiation(self) -> None:
        """Test CustomViolationsTable can be instantiated."""
        table = CustomViolationsTable()
        assert table is not None

    def test_custom_violations_table_is_loading_reactive(self) -> None:
        """Test is_loading reactive attribute."""
        table = CustomViolationsTable()
        assert hasattr(table, "is_loading")

    def test_custom_violations_table_data_reactive(self) -> None:
        """Test data reactive attribute."""
        table = CustomViolationsTable()
        assert hasattr(table, "data")

    def test_custom_violations_table_error_reactive(self) -> None:
        """Test error reactive attribute."""
        table = CustomViolationsTable()
        assert hasattr(table, "error")

    def test_custom_violations_table_column_defs(self) -> None:
        """Test column definitions contain violation columns."""
        table = CustomViolationsTable()
        assert isinstance(table._COLUMN_DEFS, list)
        assert len(table._COLUMN_DEFS) > 0


@pytest.mark.unit
@pytest.mark.asyncio
class TestCustomViolationsTableReactive:
    """Tests for CustomViolationsTable reactive property changes."""

    async def test_watch_is_loading_does_not_raise(self) -> None:
        """Test watch_is_loading handles changes without error."""
        table = CustomViolationsTable()
        table.watch_is_loading(True)
        table.watch_is_loading(False)

    async def test_watch_data_does_not_raise(self) -> None:
        """Test watch_data handles changes without error."""
        table = CustomViolationsTable()
        test_data = [{"violation": "test"}]
        table.watch_data(test_data)

    async def test_watch_error_handles_none(self) -> None:
        """Test watch_error handles None value."""
        table = CustomViolationsTable()
        table.watch_error(None)

    async def test_watch_error_handles_message(self) -> None:
        """Test watch_error handles error message."""
        table = CustomViolationsTable()
        table.watch_error("Violations fetch failed")
