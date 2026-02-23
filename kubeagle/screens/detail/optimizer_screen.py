"""Compatibility shim for the removed standalone Optimizer screen.

Optimizer functionality is now hosted inside ChartsExplorer:
- Violations view
- AI Fix Runs pane (replaced the former embedded recommendations section)
"""

from __future__ import annotations

from kubeagle.screens.charts_explorer import ChartsExplorerScreen
from kubeagle.screens.charts_explorer.config import (
    TAB_VIOLATIONS,
)
from kubeagle.screens.detail.presenter import (
    OptimizerDataLoaded,
    OptimizerDataLoadFailed,
)


class OptimizerScreen(ChartsExplorerScreen):
    """Backward-compatible alias that opens ChartsExplorer optimizer tabs."""

    def __init__(
        self,
        team_filter: str | None = None,
        testing: bool = False,
        include_cluster: bool = True,
    ) -> None:
        self.team_filter = team_filter
        self._include_cluster = include_cluster
        super().__init__(
            initial_tab=TAB_VIOLATIONS,
            team_filter=team_filter,
            include_cluster=include_cluster,
            testing=testing,
        )
        self._current_view = "violations"

    def action_view_violations(self) -> None:
        self._current_view = "violations"
        self.action_show_violations_tab()

    def action_show_violations_tab(self) -> None:
        self._current_view = "violations"
        super().action_show_violations_tab()


__all__ = [
    "OptimizerDataLoadFailed",
    "OptimizerDataLoaded",
    "OptimizerScreen",
]
