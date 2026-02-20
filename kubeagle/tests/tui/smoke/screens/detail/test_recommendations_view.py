"""Smoke tests for recommendations view behavior inside OptimizerScreen."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from textual.app import App
from textual.widgets import Select

from kubeagle.screens.detail import OptimizerScreen
from kubeagle.screens.detail.components import RecommendationsView
from kubeagle.widgets import (
    CustomContainer,
    CustomMarkdownViewer,
    CustomStatic,
)
from kubeagle.widgets.special.custom_tree import CustomTree


class TestRecommendationsViewRuntime:
    """Runtime behavior checks for recommendations rendering."""

    @pytest.mark.asyncio
    async def test_populates_tree_after_data_update(self, app: App) -> None:
        """Recommendations should render as a tree once data is updated."""
        async with app.run_test(size=(160, 50)) as pilot:
            screen = OptimizerScreen(testing=True, initial_view="recommendations")
            app.push_screen(screen)
            await pilot.pause()

            view = screen.query_one("#recommendations-view", RecommendationsView)
            recommendations = [
                {
                    "title": "Set resource requests",
                    "description": "Configure CPU and memory requests.",
                    "category": "resources",
                    "severity": "critical",
                    "affected_resources": ["chart-a"],
                    "recommended_action": "Add requests to values.yaml.",
                },
                {
                    "title": "Add PDB",
                    "description": "Protect disruption-sensitive workloads.",
                    "category": "availability",
                    "severity": "warning",
                    "affected_resources": ["chart-b"],
                    "recommended_action": "Create a podDisruptionBudget.",
                },
            ]
            charts = [SimpleNamespace(name="chart-a"), SimpleNamespace(name="chart-b")]

            view.update_data(recommendations, charts)
            await asyncio.sleep(0.2)

            tree = view.query_one("#rec-recommendations-tree", CustomTree)
            assert len(tree.root.children) == 2

    @pytest.mark.asyncio
    async def test_shows_filter_empty_state_message(self, app: App) -> None:
        """Filter-only empty states should explain that current filters hid data."""
        async with app.run_test(size=(160, 50)) as pilot:
            screen = OptimizerScreen(testing=True, initial_view="recommendations")
            app.push_screen(screen)
            await pilot.pause()

            view = screen.query_one("#recommendations-view", RecommendationsView)
            recommendations = [
                {
                    "title": "Set resource requests",
                    "description": "Configure CPU and memory requests.",
                    "category": "resources",
                    "severity": "critical",
                    "affected_resources": ["chart-a"],
                    "recommended_action": "Add requests to values.yaml.",
                },
            ]
            charts = [SimpleNamespace(name="chart-a")]

            view.update_data(recommendations, charts)
            view.severity_filter = {"warning"}
            view._apply_filters()
            await asyncio.sleep(0.1)

            empty_state = view.query_one("#rec-empty-state", CustomStatic)
            assert "match the current filters" in str(empty_state.content)

    @pytest.mark.asyncio
    async def test_loading_overlay_toggles_after_data_update(self, app: App) -> None:
        """Recommendations loading overlay should hide after data is provided."""
        async with app.run_test(size=(160, 50)) as pilot:
            screen = OptimizerScreen(testing=True, initial_view="recommendations")
            app.push_screen(screen)
            await pilot.pause()

            view = screen.query_one("#recommendations-view", RecommendationsView)
            overlay = view.query_one("#rec-loading-overlay", CustomContainer)
            assert overlay.display is True

            recommendations = [
                {
                    "title": "Set resource requests",
                    "description": "Configure CPU and memory requests.",
                    "category": "resources",
                    "severity": "critical",
                    "affected_resources": ["chart-a"],
                    "recommended_action": "Add requests to values.yaml.",
                },
            ]
            charts = [SimpleNamespace(name="chart-a")]

            view.update_data(recommendations, charts)
            await asyncio.sleep(0.1)
            assert overlay.display is False

    @pytest.mark.asyncio
    async def test_sort_dropdown_updates_sort_state(self, app: App) -> None:
        """Sort and order dropdowns should update runtime sort state."""
        async with app.run_test(size=(160, 50)) as pilot:
            screen = OptimizerScreen(testing=True, initial_view="recommendations")
            app.push_screen(screen)
            await pilot.pause()

            view = screen.query_one("#recommendations-view", RecommendationsView)
            view.update_data([], [])
            await asyncio.sleep(0.1)

            sort_select = view.query_one("#rec-sort-select", Select)
            order_select = view.query_one("#rec-order-select", Select)

            sort_select.value = "title"
            order_select.value = "desc"
            await asyncio.sleep(0.1)

            assert view.sort_by == "title"
            assert view.sort_order == "desc"

    @pytest.mark.asyncio
    async def test_details_panel_uses_markdown_viewer(self, app: App) -> None:
        """Details panel should render recommendation content via markdown viewer."""
        async with app.run_test(size=(160, 50)) as pilot:
            screen = OptimizerScreen(testing=True, initial_view="recommendations")
            app.push_screen(screen)
            await pilot.pause()

            view = screen.query_one("#recommendations-view", RecommendationsView)
            details = view.query_one("#rec-details", CustomMarkdownViewer)
            assert details is not None

    @pytest.mark.asyncio
    async def test_builds_markdown_recommendation_preview(self, app: App) -> None:
        """Markdown preview content should include headers, lists, and YAML fenced blocks."""
        async with app.run_test(size=(160, 50)) as pilot:
            screen = OptimizerScreen(testing=True, initial_view="recommendations")
            app.push_screen(screen)
            await pilot.pause()

            view = screen.query_one("#recommendations-view", RecommendationsView)
            markdown = view._build_recommendation_markdown(
                {
                    "title": "Set resource requests",
                    "description": "Tune resources:\n  - CPU\n  - Memory",
                    "category": "resources",
                    "severity": "critical",
                    "affected_resources": ["chart-a", "chart-b"],
                    "recommended_action": "Add requests in values.yaml",
                    "yaml_example": "resources:\n  requests:\n    cpu: 100m",
                }
            )

            assert "### Set resource requests" in markdown
            assert "- **Severity:** `CRITICAL`" in markdown
            assert "- CPU" in markdown
            assert "- `chart-a`" in markdown
            assert "```yaml" in markdown
