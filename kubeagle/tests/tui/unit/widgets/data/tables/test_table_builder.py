"""Tests for DataTableBuilder utility functions.

Tests cover:
- DataTableBuilder class instantiation
- Table creation methods
- Column configuration
- Row addition
"""

from __future__ import annotations

import pytest

from kubeagle.widgets.data.tables.table_builder import DataTableBuilder

# =============================================================================
# DataTableBuilder Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.fast
class TestDataTableBuilder:
    """Tests for DataTableBuilder utility class."""

    def test_data_table_builder_instantiation(self) -> None:
        """Test DataTableBuilder can be instantiated."""
        builder = DataTableBuilder()
        assert builder is not None

    def test_data_table_builder_with_id(self) -> None:
        """Test DataTableBuilder with custom ID."""
        builder = DataTableBuilder(id="custom-table")
        assert builder._id == "custom-table"

    def test_data_table_builder_columns_initial_empty(self) -> None:
        """Test columns list is initially empty."""
        builder = DataTableBuilder()
        assert builder._columns == []

    def test_data_table_builder_rows_initial_empty(self) -> None:
        """Test rows list is initially empty."""
        builder = DataTableBuilder()
        assert builder._rows == []


# =============================================================================
# DataTableBuilder Column Configuration Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.fast
class TestDataTableBuilderColumns:
    """Tests for DataTableBuilder column configuration."""

    def test_data_table_builder_add_column(self) -> None:
        """Test add_column method returns self for chaining."""
        from kubeagle.models.types.columns import ColumnDef

        builder = DataTableBuilder()
        column = ColumnDef(label="Test", key="test")
        result = builder.add_column(column)
        assert result is builder
        assert len(builder._columns) == 1

    def test_data_table_builder_add_multiple_columns(self) -> None:
        """Test adding multiple columns."""
        from kubeagle.models.types.columns import ColumnDef

        builder = DataTableBuilder()
        builder.add_column(ColumnDef(label="Col1", key="col1"))
        builder.add_column(ColumnDef(label="Col2", key="col2"))
        builder.add_column(ColumnDef(label="Col3", key="col3"))
        assert len(builder._columns) == 3


# =============================================================================
# DataTableBuilder Row Addition Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.fast
class TestDataTableBuilderRows:
    """Tests for DataTableBuilder row addition."""

    def test_data_table_builder_add_row(self) -> None:
        """Test add_row method returns self for chaining."""
        builder = DataTableBuilder()
        result = builder.add_row("value1", "value2")
        assert result is builder
        assert len(builder._rows) == 1
        assert builder._rows[0] == ("value1", "value2")

    def test_data_table_builder_add_multiple_rows(self) -> None:
        """Test adding multiple rows."""
        builder = DataTableBuilder()
        builder.add_row("row1col1", "row1col2")
        builder.add_row("row2col1", "row2col2")
        builder.add_row("row3col1", "row3col2")
        assert len(builder._rows) == 3


# =============================================================================
# DataTableBuilder Build Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.fast
class TestDataTableBuilderBuild:
    """Tests for DataTableBuilder build method."""

    def test_data_table_builder_build_returns_datatable(self) -> None:
        """Test build method returns a DataTable widget."""
        from textual.widgets import DataTable

        builder = DataTableBuilder()
        table = builder.build()
        assert isinstance(table, DataTable)

    def test_data_table_builder_build_with_id(self) -> None:
        """Test building table with custom ID."""
        builder = DataTableBuilder(id="my-table")
        table = builder.build()
        assert table.id == "my-table"
