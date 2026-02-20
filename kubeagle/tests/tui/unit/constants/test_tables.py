"""Unit tests for table column configurations in constants/tables.py.

Tests cover:
- ColumnWidth NamedTuple structure
- All table column definition lists
- Column tuples are (str, int)
- Widths are positive
- No duplicate column names within a table
"""

from __future__ import annotations

import pytest

from kubeagle.constants.tables import (
    CLUSTER_EVENTS_COLUMNS,
    CLUSTER_NODE_DIST_COLUMNS,
    CLUSTER_NODE_GROUPS_COLUMNS,
    CLUSTER_NODES_COLUMNS,
    CLUSTER_PDBS_COLUMNS,
    CLUSTER_PODS_COLUMNS,
    CLUSTER_SINGLE_REPLICA_COLUMNS,
    CLUSTER_STATS_COLUMNS,
    ColumnWidth,
)

# =============================================================================
# ColumnWidth NamedTuple
# =============================================================================


class TestColumnWidth:
    """Test ColumnWidth NamedTuple."""

    def test_create_column_width(self) -> None:
        col = ColumnWidth("Name", 30)
        assert col.label == "Name"
        assert col.width == 30

    def test_column_width_is_tuple(self) -> None:
        col = ColumnWidth("Name", 30)
        assert isinstance(col, tuple)

    def test_column_width_unpacking(self) -> None:
        col = ColumnWidth("Status", 12)
        label, width = col
        assert label == "Status"
        assert width == 12

    def test_column_width_length(self) -> None:
        col = ColumnWidth("Name", 30)
        assert len(col) == 2


# =============================================================================
# Column definition helper
# =============================================================================

ALL_COLUMN_DEFINITIONS = [
    ("CLUSTER_NODES_COLUMNS", CLUSTER_NODES_COLUMNS),
    ("CLUSTER_PODS_COLUMNS", CLUSTER_PODS_COLUMNS),
    ("CLUSTER_EVENTS_COLUMNS", CLUSTER_EVENTS_COLUMNS),
    ("CLUSTER_PDBS_COLUMNS", CLUSTER_PDBS_COLUMNS),
    ("CLUSTER_SINGLE_REPLICA_COLUMNS", CLUSTER_SINGLE_REPLICA_COLUMNS),
    ("CLUSTER_NODE_DIST_COLUMNS", CLUSTER_NODE_DIST_COLUMNS),
    ("CLUSTER_NODE_GROUPS_COLUMNS", CLUSTER_NODE_GROUPS_COLUMNS),
    ("CLUSTER_STATS_COLUMNS", CLUSTER_STATS_COLUMNS),
]


# =============================================================================
# Cluster nodes columns
# =============================================================================


class TestClusterNodesColumns:
    """Test CLUSTER_NODES_COLUMNS definition."""

    def test_count(self) -> None:
        assert len(CLUSTER_NODES_COLUMNS) == 6

    def test_first_column_is_name(self) -> None:
        assert CLUSTER_NODES_COLUMNS[0].label == "Name"

    def test_has_status_column(self) -> None:
        labels = [col.label for col in CLUSTER_NODES_COLUMNS]
        assert "Status" in labels


# =============================================================================
# Cluster pods columns
# =============================================================================


class TestClusterPodsColumns:
    """Test CLUSTER_PODS_COLUMNS definition."""

    def test_count(self) -> None:
        assert len(CLUSTER_PODS_COLUMNS) == 6

    def test_first_column_is_namespace(self) -> None:
        assert CLUSTER_PODS_COLUMNS[0].label == "Namespace"


# =============================================================================
# Cluster events columns
# =============================================================================


class TestClusterEventsColumns:
    """Test CLUSTER_EVENTS_COLUMNS definition."""

    def test_count(self) -> None:
        assert len(CLUSTER_EVENTS_COLUMNS) == 5

    def test_first_column_is_time(self) -> None:
        assert CLUSTER_EVENTS_COLUMNS[0].label == "Time"


# =============================================================================
# Cluster PDbs columns
# =============================================================================


class TestClusterPdbsColumns:
    """Test CLUSTER_PDBS_COLUMNS definition."""

    def test_count(self) -> None:
        assert len(CLUSTER_PDBS_COLUMNS) == 5

    def test_first_column_is_namespace(self) -> None:
        assert CLUSTER_PDBS_COLUMNS[0].label == "Namespace"


# =============================================================================
# Cluster single replica columns
# =============================================================================


class TestClusterSingleReplicaColumns:
    """Test CLUSTER_SINGLE_REPLICA_COLUMNS definition."""

    def test_count(self) -> None:
        assert len(CLUSTER_SINGLE_REPLICA_COLUMNS) == 5


# =============================================================================
# Cluster node distribution columns
# =============================================================================


class TestClusterNodeDistColumns:
    """Test CLUSTER_NODE_DIST_COLUMNS definition."""

    def test_count(self) -> None:
        assert len(CLUSTER_NODE_DIST_COLUMNS) == 7

    def test_first_column_is_node(self) -> None:
        assert CLUSTER_NODE_DIST_COLUMNS[0].label == "Node"


# =============================================================================
# Cluster node groups columns
# =============================================================================


class TestClusterNodeGroupsColumns:
    """Test CLUSTER_NODE_GROUPS_COLUMNS definition."""

    def test_count(self) -> None:
        assert len(CLUSTER_NODE_GROUPS_COLUMNS) == 6

    def test_first_column_is_node_group(self) -> None:
        assert CLUSTER_NODE_GROUPS_COLUMNS[0].label == "Node Group"


# =============================================================================
# Cluster stats columns
# =============================================================================


class TestClusterStatsColumns:
    """Test CLUSTER_STATS_COLUMNS definition."""

    def test_count(self) -> None:
        assert len(CLUSTER_STATS_COLUMNS) == 3

    def test_first_column_is_category(self) -> None:
        assert CLUSTER_STATS_COLUMNS[0].label == "Category"


# =============================================================================
# Generic tests applied to all column lists
# =============================================================================


class TestAllColumnDefinitions:
    """Generic tests applied to all column definition lists."""

    @pytest.mark.parametrize("name,columns", ALL_COLUMN_DEFINITIONS)
    def test_all_columns_are_column_width(self, name: str, columns: list[ColumnWidth]) -> None:
        for col in columns:
            assert isinstance(col, ColumnWidth), f"{name}: {col} is not a ColumnWidth"

    @pytest.mark.parametrize("name,columns", ALL_COLUMN_DEFINITIONS)
    def test_all_labels_are_strings(self, name: str, columns: list[ColumnWidth]) -> None:
        for col in columns:
            assert isinstance(col.label, str), f"{name}: label {col.label} is not a string"

    @pytest.mark.parametrize("name,columns", ALL_COLUMN_DEFINITIONS)
    def test_all_widths_are_ints(self, name: str, columns: list[ColumnWidth]) -> None:
        for col in columns:
            assert isinstance(col.width, int), f"{name}: width {col.width} is not an int"

    @pytest.mark.parametrize("name,columns", ALL_COLUMN_DEFINITIONS)
    def test_all_widths_positive(self, name: str, columns: list[ColumnWidth]) -> None:
        for col in columns:
            assert col.width > 0, f"{name}: width for '{col.label}' must be > 0"

    @pytest.mark.parametrize("name,columns", ALL_COLUMN_DEFINITIONS)
    def test_all_labels_non_empty(self, name: str, columns: list[ColumnWidth]) -> None:
        for col in columns:
            assert len(col.label) > 0, f"{name}: column label must not be empty"

    @pytest.mark.parametrize("name,columns", ALL_COLUMN_DEFINITIONS)
    def test_no_duplicate_labels(self, name: str, columns: list[ColumnWidth]) -> None:
        labels = [col.label for col in columns]
        assert len(labels) == len(set(labels)), f"{name}: duplicate column labels found"

    @pytest.mark.parametrize("name,columns", ALL_COLUMN_DEFINITIONS)
    def test_columns_not_empty(self, name: str, columns: list[ColumnWidth]) -> None:
        assert len(columns) > 0, f"{name}: column list must not be empty"


# =============================================================================
# __all__ exports
# =============================================================================


class TestTablesExports:
    """Test that __all__ exports are correct."""

    def test_all_exports_importable(self) -> None:
        import kubeagle.constants.tables as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"{name} listed in __all__ but not defined"
