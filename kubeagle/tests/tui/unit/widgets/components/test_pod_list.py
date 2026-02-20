"""Unit tests for PodListComponent.

Tests the cluster screen's PodListComponent, which provides
table lookup and update operations for pod data display.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from kubeagle.screens.cluster.components.pod_list import (
    PodListComponent,
)

# ---------------------------------------------------------------------------
# Instantiation
# ---------------------------------------------------------------------------


class TestPodListComponentInit:
    """Tests for PodListComponent initialization."""

    def test_default_table_id(self) -> None:
        """Default table_id should be 'pods-table'."""
        component = PodListComponent()
        assert component.table_id == "pods-table"

    def test_custom_table_id(self) -> None:
        """Custom table_id should be accepted and stored."""
        component = PodListComponent(table_id="custom-pods")
        assert component.table_id == "custom-pods"

    def test_empty_table_id(self) -> None:
        """Empty string table_id should be accepted."""
        component = PodListComponent(table_id="")
        assert component.table_id == ""


# ---------------------------------------------------------------------------
# get_table
# ---------------------------------------------------------------------------


class TestPodListComponentGetTable:
    """Tests for PodListComponent.get_table method."""

    def test_get_table_returns_widget_when_found(self) -> None:
        """get_table should return the CustomDataTable widget when it exists."""
        component = PodListComponent(table_id="pods-table")
        mock_table = MagicMock()
        mock_parent = MagicMock()
        mock_parent.query_one.return_value = mock_table

        result = component.get_table(mock_parent)

        assert result is mock_table
        mock_parent.query_one.assert_called_once()
        call_args = mock_parent.query_one.call_args
        assert "#pods-table" in call_args[0][0]

    def test_get_table_returns_none_on_query_error(self) -> None:
        """get_table should return None when the widget is not found."""
        from textual.css.query import QueryError

        component = PodListComponent(table_id="missing-table")
        mock_parent = MagicMock()
        mock_parent.query_one.side_effect = QueryError("not found")

        result = component.get_table(mock_parent)

        assert result is None

    def test_get_table_uses_custom_id_in_selector(self) -> None:
        """get_table should use the configured table_id in the CSS selector."""
        component = PodListComponent(table_id="my-custom-id")
        mock_parent = MagicMock()
        mock_parent.query_one.return_value = MagicMock()

        component.get_table(mock_parent)

        call_args = mock_parent.query_one.call_args
        assert "#my-custom-id" in call_args[0][0]


# ---------------------------------------------------------------------------
# update_table
# ---------------------------------------------------------------------------


class TestPodListComponentUpdateTable:
    """Tests for PodListComponent.update_table method."""

    def test_update_table_calls_get_table(self) -> None:
        """update_table should attempt to locate the table widget."""
        component = PodListComponent()
        mock_parent = MagicMock()
        # Make get_table return None so update_table exits early
        with patch.object(component, "get_table", return_value=None) as mock_get:
            component.update_table(mock_parent, [])
            mock_get.assert_called_once_with(mock_parent)

    def test_update_table_returns_early_when_table_not_found(self) -> None:
        """update_table should return without error when table is not found."""
        component = PodListComponent()
        mock_parent = MagicMock()
        with patch.object(component, "get_table", return_value=None):
            # Should not raise
            component.update_table(mock_parent, [{"name": "pod-1"}])

    def test_update_table_with_empty_pods(self) -> None:
        """update_table should accept an empty pod list without error."""
        component = PodListComponent()
        mock_table = MagicMock()
        mock_parent = MagicMock()
        with patch.object(component, "get_table", return_value=mock_table):
            component.update_table(mock_parent, [])

    def test_update_table_with_pod_data(self) -> None:
        """update_table should accept a list of pod dictionaries."""
        component = PodListComponent()
        mock_table = MagicMock()
        mock_parent = MagicMock()
        pods = [
            {"name": "pod-1", "namespace": "default", "status": "Running"},
            {"name": "pod-2", "namespace": "kube-system", "status": "Pending"},
        ]
        with patch.object(component, "get_table", return_value=mock_table):
            component.update_table(mock_parent, pods)

    def test_update_table_passes_parent_to_get_table(self) -> None:
        """update_table should forward the parent argument to get_table."""
        component = PodListComponent()
        mock_parent = MagicMock()
        with patch.object(component, "get_table", return_value=None) as mock_get:
            component.update_table(mock_parent, [])
            mock_get.assert_called_once_with(mock_parent)


# ---------------------------------------------------------------------------
# Module-level import test
# ---------------------------------------------------------------------------


class TestPodListComponentImports:
    """Tests that PodListComponent can be imported from the components package."""

    def test_import_from_components_package(self) -> None:
        """PodListComponent should be importable from the cluster components package."""
        from kubeagle.screens.cluster.components import (
            PodListComponent as ImportedClass,
        )

        assert ImportedClass is PodListComponent

    def test_import_from_pod_list_module(self) -> None:
        """PodListComponent should be importable from the pod_list module."""
        from kubeagle.screens.cluster.components.pod_list import (
            PodListComponent as DirectImport,
        )

        assert DirectImport is PodListComponent
