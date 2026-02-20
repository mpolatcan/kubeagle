"""Unit tests for ChartDetailViewComponent.

Tests the detail screen's ChartDetailViewComponent, which provides
view update operations for chart detail information display.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from kubeagle.screens.detail.components.chart_detail_view import (
    ChartDetailViewComponent,
)

# ---------------------------------------------------------------------------
# Instantiation
# ---------------------------------------------------------------------------


class TestChartDetailViewComponentInit:
    """Tests for ChartDetailViewComponent initialization."""

    def test_default_widget_id(self) -> None:
        """Default widget_id should be 'chart-detail-view'."""
        component = ChartDetailViewComponent()
        assert component.widget_id == "chart-detail-view"

    def test_custom_widget_id(self) -> None:
        """Custom widget_id should be accepted and stored."""
        component = ChartDetailViewComponent(widget_id="my-detail-view")
        assert component.widget_id == "my-detail-view"

    def test_empty_widget_id(self) -> None:
        """Empty string widget_id should be accepted."""
        component = ChartDetailViewComponent(widget_id="")
        assert component.widget_id == ""

    def test_widget_id_stored_as_attribute(self) -> None:
        """widget_id should be accessible as an instance attribute."""
        component = ChartDetailViewComponent(widget_id="test-id")
        assert hasattr(component, "widget_id")
        assert component.widget_id == "test-id"


# ---------------------------------------------------------------------------
# update_view
# ---------------------------------------------------------------------------


class TestChartDetailViewComponentUpdateView:
    """Tests for ChartDetailViewComponent.update_view method."""

    def test_update_view_with_empty_dict(self) -> None:
        """update_view should accept an empty chart_info dict without error."""
        component = ChartDetailViewComponent()
        mock_parent = MagicMock()
        component.update_view(mock_parent, {})

    def test_update_view_with_chart_info(self) -> None:
        """update_view should accept a populated chart_info dict."""
        component = ChartDetailViewComponent()
        mock_parent = MagicMock()
        chart_info = {
            "name": "nginx-chart",
            "version": "1.0.0",
            "team": "platform",
            "cpu_request": 100,
            "memory_request": 256,
        }
        component.update_view(mock_parent, chart_info)

    def test_update_view_with_none_parent(self) -> None:
        """update_view should handle None parent gracefully (current impl is pass)."""
        component = ChartDetailViewComponent()
        # The current implementation is a pass, so this should not raise
        component.update_view(None, {"name": "test"})

    def test_update_view_accepts_any_parent_type(self) -> None:
        """update_view parent parameter is untyped and accepts any object."""
        component = ChartDetailViewComponent()
        # Pass different parent types - all should work since impl is pass
        component.update_view(MagicMock(), {"key": "value"})
        component.update_view("string-parent", {"key": "value"})
        component.update_view(42, {"key": "value"})

    def test_update_view_returns_none(self) -> None:
        """update_view should return None (implicit from pass)."""
        component = ChartDetailViewComponent()
        result = component.update_view(MagicMock(), {"name": "chart"})
        assert result is None

    def test_update_view_with_nested_chart_info(self) -> None:
        """update_view should accept nested dict structures in chart_info."""
        component = ChartDetailViewComponent()
        mock_parent = MagicMock()
        chart_info = {
            "name": "complex-chart",
            "resources": {
                "cpu": {"request": 100, "limit": 200},
                "memory": {"request": 128, "limit": 512},
            },
            "probes": {"liveness": True, "readiness": True, "startup": False},
        }
        component.update_view(mock_parent, chart_info)


# ---------------------------------------------------------------------------
# Module-level import test
# ---------------------------------------------------------------------------


class TestChartDetailViewComponentImports:
    """Tests that ChartDetailViewComponent can be imported from the components package."""

    def test_import_from_components_package(self) -> None:
        """ChartDetailViewComponent should be importable from the detail components package."""
        from kubeagle.screens.detail.components import (
            ChartDetailViewComponent as ImportedClass,
        )

        assert ImportedClass is ChartDetailViewComponent

    def test_import_from_chart_detail_view_module(self) -> None:
        """ChartDetailViewComponent should be importable from the chart_detail_view module."""
        from kubeagle.screens.detail.components.chart_detail_view import (
            ChartDetailViewComponent as DirectImport,
        )

        assert DirectImport is ChartDetailViewComponent
