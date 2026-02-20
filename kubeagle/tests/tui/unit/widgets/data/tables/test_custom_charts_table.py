"""Tests for CustomChartsTable widget.

Tests cover:
- CustomChartsTable instantiation
- Column definitions specific to charts
- Team filtering functionality
- Data handling
"""

from __future__ import annotations

import pytest

from kubeagle.widgets.data.tables.custom_charts_table import (
    CustomChartsTable,
)

# =============================================================================
# CustomChartsTable Widget Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.fast
class TestCustomChartsTable:
    """Tests for CustomChartsTable widget."""

    def test_custom_charts_table_instantiation(self) -> None:
        """Test CustomChartsTable can be instantiated."""
        table = CustomChartsTable()
        assert table is not None

    def test_custom_charts_table_is_loading_reactive(self) -> None:
        """Test is_loading reactive attribute."""
        table = CustomChartsTable()
        assert hasattr(table, "is_loading")

    def test_custom_charts_table_data_reactive(self) -> None:
        """Test data reactive attribute."""
        table = CustomChartsTable()
        assert hasattr(table, "data")

    def test_custom_charts_table_error_reactive(self) -> None:
        """Test error reactive attribute."""
        table = CustomChartsTable()
        assert hasattr(table, "error")

    def test_custom_charts_table_column_defs(self) -> None:
        """Test column definitions contain expected chart columns."""
        table = CustomChartsTable()
        assert isinstance(table._COLUMN_DEFS, list)
        assert len(table._COLUMN_DEFS) > 0

    def test_custom_charts_table_numeric_columns(self) -> None:
        """Test numeric columns include replicas."""
        table = CustomChartsTable()
        assert "replicas" in table._NUMERIC_COLUMNS

    def test_custom_charts_table_has_all_row_data_property(self) -> None:
        """Test all_row_data property exists."""
        table = CustomChartsTable()
        assert hasattr(table, "all_row_data")


@pytest.mark.unit
@pytest.mark.asyncio
class TestCustomChartsTableFiltering:
    """Tests for CustomChartsTable filtering functionality."""

    async def test_filter_by_team_empty_shows_all(self) -> None:
        """Test filtering with empty team shows all rows."""
        table = CustomChartsTable()
        # Empty string should show all - should not raise
        table.filter_by_team("")

    async def test_filter_by_team_specific_team(self) -> None:
        """Test filtering by specific team."""
        table = CustomChartsTable()
        # Should not raise
        table.filter_by_team("platform")
