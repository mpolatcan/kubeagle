"""Init file for detail components."""

from kubeagle.screens.detail.components.chart_detail_view import (
    ChartDetailViewComponent,
)
from kubeagle.screens.detail.components.recommendations_view import (
    RecommendationsView,
)
from kubeagle.screens.detail.components.violations_view import (
    ViolationRefreshRequested,
    ViolationsView,
)

__all__ = [
    "ChartDetailViewComponent",
    "RecommendationsView",
    "ViolationRefreshRequested",
    "ViolationsView",
]
