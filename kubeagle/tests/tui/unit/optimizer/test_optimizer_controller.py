"""Tests for unified optimizer controller resource unit formatting."""

from __future__ import annotations

import time
from pathlib import Path

from kubeagle.constants.enums import QoSClass
from kubeagle.models.charts.chart_info import ChartInfo
from kubeagle.models.optimization.optimization_violation import (
    OptimizationViolation,
)
from kubeagle.models.optimization.optimizer_controller import (
    UnifiedOptimizerController,
)
from kubeagle.optimizer.helm_renderer import HelmRenderResult


def _make_chart() -> ChartInfo:
    return ChartInfo(
        name="payments-api",
        team="payments",
        values_file="/tmp/payments/values.yaml",
        namespace="default",
        cpu_request=100.0,
        cpu_limit=200.0,
        memory_request=128 * 1024 * 1024,
        memory_limit=256 * 1024 * 1024,
        qos_class=QoSClass.BURSTABLE,
        has_liveness=True,
        has_readiness=True,
        has_startup=False,
        has_anti_affinity=False,
        has_topology_spread=False,
        has_topology=False,
        pdb_enabled=False,
        pdb_template_exists=False,
        pdb_min_available=None,
        pdb_max_unavailable=None,
        replicas=1,
        priority_class=None,
    )


def _make_rule_violation(rule_id: str) -> OptimizationViolation:
    return OptimizationViolation(
        rule_id=rule_id,
        name=f"Rule {rule_id}",
        description="test violation",
        severity="warning",
        category="resources",
        fix_preview=None,
        auto_fixable=True,
    )


class TestUnifiedOptimizerControllerResourceFormatting:
    """Resource unit conversion and display formatting tests."""

    def test_chart_dict_uses_millicores_and_mi(self) -> None:
        """Chart dict should convert bytes to Mi and keep CPU in millicores."""
        controller = UnifiedOptimizerController()
        chart_dict = controller._chart_info_to_dict(_make_chart())

        assert chart_dict["resources"]["requests"]["cpu"] == "100m"
        assert chart_dict["resources"]["limits"]["cpu"] == "200m"
        assert chart_dict["resources"]["requests"]["memory"] == "128Mi"
        assert chart_dict["resources"]["limits"]["memory"] == "256Mi"
        assert chart_dict["qos_class"] == "Burstable"

    def test_current_value_for_memory_ratio_uses_mi(self) -> None:
        """RES006 current value should display memory in Mi, not raw bytes."""
        controller = UnifiedOptimizerController()
        chart = _make_chart()
        violation = _make_rule_violation("RES006")

        current_value = controller._derive_current_value(violation, chart)

        assert current_value == "Mem: 128Mi req / 256Mi lim (2.0x, Burstable)"

    def test_rendered_ratio_current_value_uses_rendered_qos_label(self) -> None:
        """Rendered rule inputs should override QoS label in ratio current value."""
        controller = UnifiedOptimizerController()
        chart = _make_chart()
        chart.qos_class = QoSClass.BEST_EFFORT
        violation = _make_rule_violation("RES005")
        rendered_rule_input = {
            "qos_class": "Burstable",
            "resources": {
                "requests": {"cpu": "100m"},
                "limits": {"cpu": "400m"},
            },
        }

        current_value = controller._derive_current_value(
            violation,
            chart,
            rendered_rule_input=rendered_rule_input,
        )

        assert current_value == "CPU: 100m req / 400m lim (4.0x, Burstable)"

    def test_rendered_missing_cpu_limit_shows_missing_value(self) -> None:
        """RES002 should not fallback to chart-level limits when rendered limit is missing."""
        controller = UnifiedOptimizerController()
        chart = _make_chart()
        violation = _make_rule_violation("RES002")
        rendered_rule_input = {
            "resources": {
                "requests": {"cpu": "20m"},
                "limits": {"cpu": None},
            }
        }

        current_value = controller._derive_current_value(
            violation,
            chart,
            rendered_rule_input=rendered_rule_input,
        )

        assert current_value == "No CPU limit"

    def test_rendered_missing_memory_limit_shows_missing_value(self) -> None:
        """RES003 should not fallback to chart-level limits when rendered limit is missing."""
        controller = UnifiedOptimizerController()
        chart = _make_chart()
        violation = _make_rule_violation("RES003")
        rendered_rule_input = {
            "resources": {
                "requests": {"memory": "128Mi"},
                "limits": {"memory": None},
            }
        }

        current_value = controller._derive_current_value(
            violation,
            chart,
            rendered_rule_input=rendered_rule_input,
        )

        assert current_value == "No memory limit"

    def test_current_value_for_memory_limit_uses_mi(self) -> None:
        """RES003 current value should show Mi for memory limits."""
        controller = UnifiedOptimizerController()
        chart = _make_chart()
        violation = _make_rule_violation("RES003")

        current_value = controller._derive_current_value(violation, chart)

        assert current_value == "256Mi"

    def test_rendered_current_value_uses_rendered_resources_over_zero_chart_values(
        self,
    ) -> None:
        """Rendered violations should not show 0m when values parsing missed nested resources."""
        controller = UnifiedOptimizerController()
        chart = _make_chart()
        chart.cpu_request = 0.0
        chart.cpu_limit = 0.0
        violation = _make_rule_violation("RES007")
        rendered_rule_input = {
            "resources": {
                "requests": {"cpu": "5m"},
                "limits": {"cpu": "250m"},
            }
        }

        current_value = controller._derive_current_value(
            violation,
            chart,
            rendered_rule_input=rendered_rule_input,
        )

        assert current_value == "CPU: 5m req / 250m lim"

    def test_auto_mode_falls_back_to_values_when_render_unavailable(
        self,
        monkeypatch,
        tmp_path: Path,
    ) -> None:
        """Auto mode should keep existing values-based behavior if render cannot run."""
        chart_dir = tmp_path / "payments"
        chart_dir.mkdir(parents=True, exist_ok=True)
        values_path = chart_dir / "values.yaml"
        values_path.write_text("replicaCount: 1\n", encoding="utf-8")
        (chart_dir / "Chart.yaml").write_text(
            "apiVersion: v2\nname: payments\nversion: 0.1.0\n",
            encoding="utf-8",
        )

        chart = ChartInfo(
            name="payments",
            team="payments",
            values_file=str(values_path),
            namespace="default",
            cpu_request=0.0,
            cpu_limit=0.0,
            memory_request=0.0,
            memory_limit=0.0,
            qos_class=QoSClass.BEST_EFFORT,
            has_liveness=False,
            has_readiness=False,
            has_startup=False,
            has_anti_affinity=False,
            has_topology_spread=False,
            has_topology=False,
            pdb_enabled=False,
            pdb_template_exists=False,
            pdb_min_available=None,
            pdb_max_unavailable=None,
            replicas=1,
            priority_class=None,
        )

        controller = UnifiedOptimizerController(analysis_source="auto")
        monkeypatch.setattr(
            "kubeagle.models.optimization.optimizer_controller.render_chart",
            lambda **kwargs: HelmRenderResult(
                ok=False,
                chart_dir=chart_dir,
                values_file=values_path,
                error_kind="helm_missing",
                error_message="helm not installed",
            ),
        )

        violations = controller.check_chart(chart)

        assert violations
        assert all(violation.analysis_source == "values" for violation in violations)

    def test_resolve_worker_count_respects_configured_max(self) -> None:
        """Configured max_workers should bound parallel workers."""
        controller = UnifiedOptimizerController(max_workers=3)

        assert controller._resolve_worker_count(10) == 3
        assert controller._resolve_worker_count(2) == 2

    def test_resolve_worker_count_uses_single_thread_for_small_inputs(self) -> None:
        """Values-mode checks keep single-threading for very small chart sets."""
        controller = UnifiedOptimizerController(
            max_workers=0,
            analysis_source="values",
        )

        assert controller._resolve_worker_count(3) == 1

    def test_resolve_worker_count_parallelizes_small_rendered_inputs(
        self,
        monkeypatch,
    ) -> None:
        """Rendered-mode checks should parallelize even for small chart sets."""
        controller = UnifiedOptimizerController(
            max_workers=0,
            analysis_source="auto",
        )
        monkeypatch.setattr(
            "kubeagle.models.optimization.optimizer_controller.os.cpu_count",
            lambda: 8,
        )

        assert controller._resolve_worker_count(3) == 3

    def test_resolve_worker_count_caps_auto_workers(self, monkeypatch) -> None:
        """Auto worker selection should respect upper bound for stability."""
        controller = UnifiedOptimizerController(max_workers=0)
        monkeypatch.setattr(
            "kubeagle.models.optimization.optimizer_controller.os.cpu_count",
            lambda: 32,
        )

        assert controller._resolve_worker_count(100) == 10

    def test_auto_mode_skips_render_when_helm_missing(self, monkeypatch) -> None:
        """Auto mode should skip rendered checks when helm binary is unavailable."""
        controller = UnifiedOptimizerController(analysis_source="auto")
        chart = _make_chart()
        which_calls = 0

        def _which(_: str) -> None:
            nonlocal which_calls
            which_calls += 1
            return None

        def _unexpected_render(**_: object) -> HelmRenderResult:
            raise AssertionError("render_chart should not be called when helm is missing")

        monkeypatch.setattr(
            "kubeagle.models.optimization.optimizer_controller.shutil.which",
            _which,
        )
        monkeypatch.setattr(
            "kubeagle.models.optimization.optimizer_controller.render_chart",
            _unexpected_render,
        )

        violations_first = controller.check_chart(chart)
        violations_second = controller.check_chart(chart)

        assert violations_first
        assert violations_second
        assert which_calls == 1

    def test_check_all_charts_progress_callback_reports_each_chart(
        self,
        monkeypatch,
    ) -> None:
        """Progress callback should be called once per chart in sequential mode."""
        controller = UnifiedOptimizerController(analysis_source="values")
        chart_one = _make_chart().model_copy(update={"name": "chart-one"})
        chart_two = _make_chart().model_copy(update={"name": "chart-two"})
        charts = [chart_one, chart_two]
        callback_calls: list[tuple[str, int, int]] = []

        monkeypatch.setattr(
            UnifiedOptimizerController,
            "_resolve_worker_count",
            lambda _self, _count: 1,
        )
        monkeypatch.setattr(
            UnifiedOptimizerController,
            "check_chart",
            lambda _self, _chart: [],
        )

        controller.check_all_charts_with_progress(
            charts,
            on_chart_done=lambda chart, _violations, completed, total: callback_calls.append(
                (chart.name, completed, total)
            ),
        )

        assert callback_calls == [
            ("chart-one", 1, 2),
            ("chart-two", 2, 2),
        ]

    def test_check_all_charts_progress_callback_reports_parallel_completion(
        self,
        monkeypatch,
    ) -> None:
        """Progress callback should report completed count in parallel mode."""
        controller = UnifiedOptimizerController(analysis_source="values")
        chart_slow = _make_chart().model_copy(update={"name": "chart-slow"})
        chart_fast = _make_chart().model_copy(update={"name": "chart-fast"})
        charts = [chart_slow, chart_fast]
        callback_calls: list[tuple[str, int, int]] = []

        monkeypatch.setattr(
            UnifiedOptimizerController,
            "_resolve_worker_count",
            lambda _self, _count: 2,
        )

        def _check_chart(_self: UnifiedOptimizerController, chart: ChartInfo) -> list:
            if chart.name == "chart-slow":
                time.sleep(0.05)
            return []

        monkeypatch.setattr(UnifiedOptimizerController, "check_chart", _check_chart)

        controller.check_all_charts_with_progress(
            charts,
            on_chart_done=lambda chart, _violations, completed, total: callback_calls.append(
                (chart.name, completed, total)
            ),
        )

        assert {name for name, _, _ in callback_calls} == {"chart-slow", "chart-fast"}
        assert [completed for _, completed, _ in callback_calls] == [1, 2]
        assert all(total == 2 for _, _, total in callback_calls)
