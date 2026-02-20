"""Unit tests for GenericTableComponent in widgets/data/tables/table_component.py.

Tests cover:
- GenericTableComponent initialization
- get_table method behavior
- update_table method behavior
- clear_table method behavior
"""

from __future__ import annotations

from unittest.mock import MagicMock

from kubeagle.widgets.data.tables.table_component import (
    GenericTableComponent,
)

# =============================================================================
# Initialization
# =============================================================================


class TestGenericTableComponentInit:
    """Test GenericTableComponent initialization."""

    def test_default_table_id(self) -> None:
        component = GenericTableComponent()
        assert component.table_id == "data-table"

    def test_custom_table_id(self) -> None:
        component = GenericTableComponent(table_id="custom-table")
        assert component.table_id == "custom-table"

    def test_table_id_stored(self) -> None:
        component = GenericTableComponent(table_id="my-table")
        assert component.table_id == "my-table"


# =============================================================================
# get_table
# =============================================================================


class TestGenericTableComponentGetTable:
    """Test GenericTableComponent.get_table method."""

    def test_returns_none_on_query_error(self) -> None:
        from textual.css.query import QueryError

        component = GenericTableComponent(table_id="test-table")
        mock_parent = MagicMock()
        mock_parent.query_one.side_effect = QueryError("")
        result = component.get_table(mock_parent)
        assert result is None

    def test_returns_table_on_success(self) -> None:
        component = GenericTableComponent(table_id="test-table")
        mock_parent = MagicMock()
        mock_table = MagicMock()
        mock_parent.query_one.return_value = mock_table
        result = component.get_table(mock_parent)
        assert result is mock_table

    def test_queries_with_correct_selector(self) -> None:
        component = GenericTableComponent(table_id="my-table")
        mock_parent = MagicMock()
        component.get_table(mock_parent)
        # The query_one call should use the #table_id selector
        call_args = mock_parent.query_one.call_args
        assert call_args[0][0] == "#my-table"


# =============================================================================
# update_table
# =============================================================================


class TestGenericTableComponentUpdateTable:
    """Test GenericTableComponent.update_table method."""

    def test_does_nothing_when_table_not_found(self) -> None:
        from textual.css.query import QueryError

        component = GenericTableComponent()
        mock_parent = MagicMock()
        mock_parent.query_one.side_effect = QueryError("")
        # Should not raise
        component.update_table(mock_parent, data=[], columns=[])

    def test_clears_table_before_update(self) -> None:
        component = GenericTableComponent()
        mock_parent = MagicMock()
        mock_table = MagicMock()
        mock_table.columns = {}  # Empty columns dict
        mock_parent.query_one.return_value = mock_table

        component.update_table(
            mock_parent,
            data=[("row1",)],
            columns=["Col1"],
        )
        mock_table.clear.assert_called_once()

    def test_adds_columns_when_empty(self) -> None:
        component = GenericTableComponent()
        mock_parent = MagicMock()
        mock_table = MagicMock()
        mock_table.columns = {}  # Empty columns - should add
        mock_parent.query_one.return_value = mock_table

        component.update_table(
            mock_parent,
            data=[],
            columns=["Name", "Status"],
        )
        assert mock_table.add_column.call_count == 2

    def test_does_not_add_columns_when_existing(self) -> None:
        component = GenericTableComponent()
        mock_parent = MagicMock()
        mock_table = MagicMock()
        # Non-empty columns means columns already exist
        mock_table.columns = {"col1": MagicMock()}
        mock_parent.query_one.return_value = mock_table

        component.update_table(
            mock_parent,
            data=[],
            columns=["Name"],
        )
        mock_table.add_column.assert_not_called()

    def test_adds_rows(self) -> None:
        component = GenericTableComponent()
        mock_parent = MagicMock()
        mock_table = MagicMock()
        mock_table.columns = {"col1": MagicMock()}  # pre-existing columns
        mock_parent.query_one.return_value = mock_table

        component.update_table(
            mock_parent,
            data=[("row1", "val1"), ("row2", "val2")],
            columns=["Name", "Value"],
        )
        assert mock_table.add_row.call_count == 2


# =============================================================================
# clear_table
# =============================================================================


class TestGenericTableComponentClearTable:
    """Test GenericTableComponent.clear_table method."""

    def test_clears_when_table_exists(self) -> None:
        component = GenericTableComponent()
        mock_parent = MagicMock()
        mock_table = MagicMock()
        mock_parent.query_one.return_value = mock_table

        component.clear_table(mock_parent)
        mock_table.clear.assert_called_once()

    def test_does_nothing_when_table_not_found(self) -> None:
        from textual.css.query import QueryError

        component = GenericTableComponent()
        mock_parent = MagicMock()
        mock_parent.query_one.side_effect = QueryError("")
        # Should not raise
        component.clear_table(mock_parent)
