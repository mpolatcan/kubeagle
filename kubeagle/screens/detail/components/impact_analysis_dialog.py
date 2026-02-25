"""Impact Analysis Dialog — modal showing resource impact for filtered violations.

Opens from the "Impact Analysis" button in the violations action bar.
Receives pre-filtered violations and charts, computes impact in a background
worker, and displays the result in a ResourceImpactView.
"""

from __future__ import annotations

import contextlib
import logging
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.screen import ModalScreen

from kubeagle.screens.detail.components.resource_impact_view import (
    ResourceImpactView,
)
from kubeagle.widgets import (
    CustomButton,
    CustomContainer,
    CustomHorizontal,
    CustomStatic,
)

if TYPE_CHECKING:
    from kubeagle.models.analysis.violation import ViolationResult
    from kubeagle.models.charts.chart_info import ChartInfo
    from kubeagle.models.optimization import UnifiedOptimizerController

logger = logging.getLogger(__name__)


class ImpactAnalysisDialog(ModalScreen[None]):
    """Modal dialog that computes and displays resource impact analysis."""

    BINDINGS = [("escape", "cancel", "Close")]

    def __init__(
        self,
        *,
        charts: list[ChartInfo],
        violations: list[ViolationResult],
        optimizer_controller: UnifiedOptimizerController,
        cluster_context: str | None = None,
    ) -> None:
        super().__init__(classes="selection-modal-screen")
        self._charts = charts
        self._violations = violations
        self._optimizer_controller = optimizer_controller
        self._cluster_context = cluster_context

    def compose(self) -> ComposeResult:
        with CustomContainer(
            classes="impact-analysis-dialog-shell selection-modal-shell",
        ):
            yield CustomStatic(
                "Impact Analysis",
                classes="selection-modal-title selection-modal-label",
                markup=False,
            )
            yield ResourceImpactView(id="impact-analysis-view")
            with CustomHorizontal(classes="selection-modal-actions"):
                yield CustomButton(
                    "Close",
                    id="impact-dialog-close-btn",
                    compact=True,
                )

    def on_mount(self) -> None:
        """Start background impact computation."""
        with contextlib.suppress(Exception):
            impact_view = self.query_one("#impact-analysis-view", ResourceImpactView)
            impact_view.set_loading(True, "Fetching cluster workloads...")
        self._compute_impact()

    def _compute_impact(self) -> None:
        """Run ResourceImpactCalculator in a background thread."""
        try:
            from kubeagle.optimizer.resource_impact_calculator import (
                ResourceImpactCalculator,
                fetch_workload_replica_map,
            )
        except Exception:
            logger.exception("Failed to import ResourceImpactCalculator")
            return

        calculator = ResourceImpactCalculator()
        charts = list(self._charts)
        violations = list(self._violations)
        controller = self._optimizer_controller
        cluster_context = self._cluster_context

        def _do_compute() -> None:
            # Fetch actual replica counts from cluster (lightweight kubectl call).
            # Always attempt the fetch — for cluster charts the map is keyed by
            # exact (release, namespace); for local charts _resolve_replicas
            # aggregates all namespaces matching the chart name.
            replica_map: dict[tuple[str, str], int] | None = None
            try:
                self.app.call_from_thread(
                    self._update_loading, "Fetching workload replicas..."
                )
                replica_map = fetch_workload_replica_map(
                    context=cluster_context,
                )
            except Exception:
                logger.debug(
                    "Failed to fetch workload replicas, using values-file defaults",
                    exc_info=True,
                )

            self.app.call_from_thread(
                self._update_loading, "Computing impact analysis..."
            )
            result = calculator.compute_impact(
                charts,
                violations,
                optimizer_controller=controller,
                workload_replica_map=replica_map,
            )
            self.app.call_from_thread(
                self._apply_result, result, charts, violations, controller,
                replica_map,
            )

        self.run_worker(_do_compute, thread=True, name="impact-dialog-compute", exclusive=True)

    def _update_loading(self, message: str) -> None:
        """Update loading message on the main thread."""
        with contextlib.suppress(Exception):
            impact_view = self.query_one("#impact-analysis-view", ResourceImpactView)
            impact_view.set_loading(True, message)

    def _apply_result(
        self,
        result: object,
        charts: list[object],
        violations: list[object],
        controller: object,
        workload_replica_map: dict[tuple[str, str], int] | None,
    ) -> None:
        """Apply the computed result to the impact view on the main thread."""
        with contextlib.suppress(Exception):
            impact_view = self.query_one("#impact-analysis-view", ResourceImpactView)
            impact_view.set_source_data(
                result,  # type: ignore[arg-type]
                charts=charts,  # type: ignore[arg-type]
                violations=violations,  # type: ignore[arg-type]
                optimizer_controller=controller,
                workload_replica_map=workload_replica_map,
            )

    def on_button_pressed(self, event: CustomButton.Pressed) -> None:
        if event.button.id == "impact-dialog-close-btn":
            self.dismiss(None)

    def on_resource_impact_view_refresh_requested(
        self, event: ResourceImpactView.RefreshRequested,
    ) -> None:
        """Handle refresh request from the impact view controls."""
        event.stop()
        with contextlib.suppress(Exception):
            impact_view = self.query_one("#impact-analysis-view", ResourceImpactView)
            impact_view.set_loading(True, "Refreshing cluster data...")
        self._compute_impact()

    def action_cancel(self) -> None:
        self.dismiss(None)
