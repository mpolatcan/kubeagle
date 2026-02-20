"""Unit tests for all enum definitions in constants/enums.py.

Tests cover:
- Each enum class and all its members
- Value correctness
- Membership tests
- String representation
- Backward-compatibility aliases
"""

from __future__ import annotations

from enum import Enum

import pytest

from kubeagle.constants.enums import (
    AppState,
    DataRefreshMode,
    FetchSources,
    FetchState,
    FilterOperator,
    LoadingState,
    NavigationMode,
    NodeStatus,
    QoSClass,
    Severity,
    SortDirection,
    SortField,
    TabState,
    ThemeMode,
    node_status,
    qos_class,
    severity,
)

# =============================================================================
# NodeStatus
# =============================================================================


class TestNodeStatus:
    """Test NodeStatus enum."""

    def test_is_enum(self) -> None:
        assert issubclass(NodeStatus, Enum)

    def test_members_count(self) -> None:
        assert len(NodeStatus) == 3

    def test_ready_value(self) -> None:
        assert NodeStatus.READY.value == "Ready"

    def test_not_ready_value(self) -> None:
        assert NodeStatus.NOT_READY.value == "NotReady"

    def test_unknown_value(self) -> None:
        assert NodeStatus.UNKNOWN.value == "Unknown"

    def test_membership(self) -> None:
        assert NodeStatus("Ready") is NodeStatus.READY

    def test_invalid_membership(self) -> None:
        with pytest.raises(ValueError):
            NodeStatus("invalid")

    def test_string_representation(self) -> None:
        assert "READY" in repr(NodeStatus.READY)


# =============================================================================
# QoSClass
# =============================================================================


class TestQoSClass:
    """Test QoSClass enum."""

    def test_is_enum(self) -> None:
        assert issubclass(QoSClass, Enum)

    def test_members_count(self) -> None:
        assert len(QoSClass) == 3

    def test_guaranteed_value(self) -> None:
        assert QoSClass.GUARANTEED.value == "Guaranteed"

    def test_burstable_value(self) -> None:
        assert QoSClass.BURSTABLE.value == "Burstable"

    def test_best_effort_value(self) -> None:
        assert QoSClass.BEST_EFFORT.value == "BestEffort"

    def test_membership(self) -> None:
        assert QoSClass("Burstable") is QoSClass.BURSTABLE


# =============================================================================
# Severity
# =============================================================================


class TestSeverity:
    """Test Severity enum."""

    def test_is_enum(self) -> None:
        assert issubclass(Severity, Enum)

    def test_members_count(self) -> None:
        assert len(Severity) == 3

    def test_error_value(self) -> None:
        assert Severity.ERROR.value == "error"

    def test_warning_value(self) -> None:
        assert Severity.WARNING.value == "warning"

    def test_info_value(self) -> None:
        assert Severity.INFO.value == "info"


# =============================================================================
# Backward compatibility aliases
# =============================================================================


class TestBackwardCompatAliases:
    """Test lowercase aliases for backward compatibility."""

    def test_node_status_alias(self) -> None:
        assert node_status is NodeStatus

    def test_qos_class_alias(self) -> None:
        assert qos_class is QoSClass

    def test_severity_alias(self) -> None:
        assert severity is Severity


# =============================================================================
# AppState
# =============================================================================


class TestAppState:
    """Test AppState enum."""

    def test_is_enum(self) -> None:
        assert issubclass(AppState, Enum)

    def test_members_count(self) -> None:
        assert len(AppState) == 4

    def test_idle_value(self) -> None:
        assert AppState.IDLE.value == "idle"

    def test_loading_value(self) -> None:
        assert AppState.LOADING.value == "loading"

    def test_error_value(self) -> None:
        assert AppState.ERROR.value == "error"

    def test_stale_value(self) -> None:
        assert AppState.STALE.value == "stale"


# =============================================================================
# LoadingState
# =============================================================================


class TestLoadingState:
    """Test LoadingState enum (alias for AppState)."""

    def test_is_enum(self) -> None:
        assert issubclass(LoadingState, Enum)

    def test_members_count(self) -> None:
        assert len(LoadingState) == 4

    def test_idle_value(self) -> None:
        assert LoadingState.IDLE.value == "idle"

    def test_loading_value(self) -> None:
        assert LoadingState.LOADING.value == "loading"

    def test_error_value(self) -> None:
        assert LoadingState.ERROR.value == "error"

    def test_stale_value(self) -> None:
        assert LoadingState.STALE.value == "stale"

    def test_same_values_as_app_state(self) -> None:
        """LoadingState should mirror AppState member values."""
        for member in AppState:
            assert hasattr(LoadingState, member.name)
            assert LoadingState[member.name].value == member.value


# =============================================================================
# FetchState
# =============================================================================


class TestFetchState:
    """Test FetchState enum."""

    def test_is_enum(self) -> None:
        assert issubclass(FetchState, Enum)

    def test_members_count(self) -> None:
        assert len(FetchState) == 3

    def test_loading_value(self) -> None:
        assert FetchState.LOADING.value == "loading"

    def test_success_value(self) -> None:
        assert FetchState.SUCCESS.value == "success"

    def test_error_value(self) -> None:
        assert FetchState.ERROR.value == "error"


# =============================================================================
# FetchSources
# =============================================================================


class TestFetchSources:
    """Test FetchSources enum."""

    def test_is_enum(self) -> None:
        assert issubclass(FetchSources, Enum)

    def test_members_count(self) -> None:
        assert len(FetchSources) == 7

    def test_nodes_value(self) -> None:
        assert FetchSources.NODES.value == "nodes"

    def test_events_value(self) -> None:
        assert FetchSources.EVENTS.value == "events"

    def test_pod_disruption_budgets_value(self) -> None:
        assert FetchSources.POD_DISRUPTION_BUDGETS.value == "pod_disruption_budgets"

    def test_helm_releases_value(self) -> None:
        assert FetchSources.HELM_RELEASES.value == "helm_releases"

    def test_node_resources_value(self) -> None:
        assert FetchSources.NODE_RESOURCES.value == "node_resources"

    def test_pod_distribution_value(self) -> None:
        assert FetchSources.POD_DISTRIBUTION.value == "pod_distribution"

    def test_cluster_connection_value(self) -> None:
        assert FetchSources.CLUSTER_CONNECTION.value == "cluster_connection"


# =============================================================================
# TabState
# =============================================================================


class TestTabState:
    """Test TabState enum (auto-valued)."""

    def test_is_enum(self) -> None:
        assert issubclass(TabState, Enum)

    def test_members_count(self) -> None:
        assert len(TabState) == 4

    def test_all_members_exist(self) -> None:
        assert hasattr(TabState, "IDLE")
        assert hasattr(TabState, "LOADING")
        assert hasattr(TabState, "LOADED")
        assert hasattr(TabState, "ERROR")

    def test_members_are_distinct(self) -> None:
        values = [m.value for m in TabState]
        assert len(values) == len(set(values))


# =============================================================================
# ThemeMode
# =============================================================================


class TestThemeMode:
    """Test ThemeMode enum."""

    def test_is_enum(self) -> None:
        assert issubclass(ThemeMode, Enum)

    def test_members_count(self) -> None:
        assert len(ThemeMode) == 2

    def test_dark_value(self) -> None:
        assert ThemeMode.DARK.value == "dark"

    def test_light_value(self) -> None:
        assert ThemeMode.LIGHT.value == "light"


# =============================================================================
# SortDirection
# =============================================================================


class TestSortDirection:
    """Test SortDirection enum."""

    def test_is_enum(self) -> None:
        assert issubclass(SortDirection, Enum)

    def test_members_count(self) -> None:
        assert len(SortDirection) == 2

    def test_asc_value(self) -> None:
        assert SortDirection.ASC.value == "asc"

    def test_desc_value(self) -> None:
        assert SortDirection.DESC.value == "desc"


# =============================================================================
# FilterOperator
# =============================================================================


class TestFilterOperator:
    """Test FilterOperator enum."""

    def test_is_enum(self) -> None:
        assert issubclass(FilterOperator, Enum)

    def test_members_count(self) -> None:
        assert len(FilterOperator) == 5

    def test_equals_value(self) -> None:
        assert FilterOperator.EQUALS.value == "eq"

    def test_not_equals_value(self) -> None:
        assert FilterOperator.NOT_EQUALS.value == "ne"

    def test_contains_value(self) -> None:
        assert FilterOperator.CONTAINS.value == "contains"

    def test_starts_with_value(self) -> None:
        assert FilterOperator.STARTS_WITH.value == "startswith"

    def test_ends_with_value(self) -> None:
        assert FilterOperator.ENDS_WITH.value == "endswith"


# =============================================================================
# DataRefreshMode
# =============================================================================


class TestDataRefreshMode:
    """Test DataRefreshMode enum."""

    def test_is_enum(self) -> None:
        assert issubclass(DataRefreshMode, Enum)

    def test_members_count(self) -> None:
        assert len(DataRefreshMode) == 3

    def test_manual_value(self) -> None:
        assert DataRefreshMode.MANUAL.value == "manual"

    def test_auto_value(self) -> None:
        assert DataRefreshMode.AUTO.value == "auto"

    def test_interval_value(self) -> None:
        assert DataRefreshMode.INTERVAL.value == "interval"


# =============================================================================
# NavigationMode
# =============================================================================


class TestNavigationMode:
    """Test NavigationMode enum."""

    def test_is_enum(self) -> None:
        assert issubclass(NavigationMode, Enum)

    def test_members_count(self) -> None:
        assert len(NavigationMode) == 3

    def test_tree_value(self) -> None:
        assert NavigationMode.TREE.value == "tree"

    def test_list_value(self) -> None:
        assert NavigationMode.LIST.value == "list"

    def test_grid_value(self) -> None:
        assert NavigationMode.GRID.value == "grid"


# =============================================================================
# SortField
# =============================================================================


class TestSortField:
    """Test SortField enum."""

    def test_is_enum(self) -> None:
        assert issubclass(SortField, Enum)

    def test_members_count(self) -> None:
        assert len(SortField) == 5

    def test_name_value(self) -> None:
        assert SortField.NAME.value == "name"

    def test_version_value(self) -> None:
        assert SortField.VERSION.value == "version"

    def test_team_value(self) -> None:
        assert SortField.TEAM.value == "team"

    def test_status_value(self) -> None:
        assert SortField.STATUS.value == "status"

    def test_created_value(self) -> None:
        assert SortField.CREATED.value == "created"


# =============================================================================
# __all__ exports
# =============================================================================


class TestEnumsExports:
    """Test that __all__ exports are correct."""

    def test_all_exports_importable(self) -> None:
        """All items in __all__ should be importable from the module."""
        import kubeagle.constants.enums as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"{name} listed in __all__ but not defined"
