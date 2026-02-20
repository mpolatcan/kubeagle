"""Phase 3 regression tests for merged Home -> Cluster overview behavior."""

from __future__ import annotations

import inspect

import pytest
from textual.app import App

from kubeagle.screens.cluster.cluster_screen import ClusterScreen
from kubeagle.widgets.feedback.custom_button import CustomButton


def test_cluster_screen_has_event_window_select_in_compose() -> None:
    """Cluster top bar should expose event lookback selector."""
    source = inspect.getsource(ClusterScreen.compose)
    assert "cluster-event-window-select" in source


def test_cluster_events_tab_has_event_details_table() -> None:
    """Events tab should render the event details table surface."""
    source = inspect.getsource(ClusterScreen.compose)
    assert "events-detail-table" in source
    assert "events-detail-table-panel" in source


def test_cluster_overview_tracks_charts_overview_source() -> None:
    """Workloads tab source map should include chart KPI payload."""
    assert "charts_overview" in ClusterScreen._TAB_DATA_KEYS["tab-pods"]


def test_cluster_stats_widget_targets_chart_kpis() -> None:
    """Workload footprint digits should be updated from dedicated updater."""
    source = inspect.getsource(ClusterScreen._update_workload_footprint_widgets)
    assert "workloads-footprint-team-total" in source
    assert "workloads-footprint-workloads-total" in source
    assert "workloads-footprint-single-charts" in source
    assert "workloads-footprint-single-ratio" in source
    assert "workloads-footprint-charts-no-template" in source
    assert "workloads-footprint-charts-no-pdb" in source


def test_cluster_workloads_table_map_has_no_workloads_tables() -> None:
    """Workloads tab should not register any table surfaces."""
    assert ClusterScreen._TAB_TABLE_IDS["tab-pods"] == ()
    assert "pdbs-table" not in ClusterScreen._TABLE_DATA_KEYS


def test_workloads_layout_places_only_pod_stats_and_footprint_panels() -> None:
    """Workloads compose order should keep two stacked summary panels only."""
    source = inspect.getsource(ClusterScreen.compose)
    assert source.index("workloads-panel-pod-request-stats") < source.index("workloads-panel-footprint")
    assert "workloads-pdb-coverage-panel" not in source
    assert "Blocking PDBs" not in source
    assert "All Workloads (Runtime)" not in source
    assert "Single Replica Workloads" not in source
    assert "workloads-inventory-panel" not in source
    assert "workloads-single-replica-panel" not in source


def test_workloads_panel_exposes_request_and_limit_pod_stats() -> None:
    """Pod stats panel should include request/limit metrics for CPU and memory."""
    source = inspect.getsource(ClusterScreen.compose)
    assert "overview-pod-cpu-req-min" in source
    assert "overview-pod-cpu-lim-p95" in source
    assert "overview-pod-mem-req-min" in source
    assert "overview-pod-mem-lim-p95" in source


def test_workloads_panel_exposes_units_dropdown() -> None:
    """Workloads pod stats panel should expose unit select dropdown."""
    source = inspect.getsource(ClusterScreen.compose)
    assert "pod-stats-units-select" in source


def test_nodes_distribution_panel_exposes_total_cpu_and_memory_digits() -> None:
    """Nodes summary should include total allocatable CPU and memory digits."""
    source = inspect.getsource(ClusterScreen.compose)
    assert "nodes-digits-total-cpu" in source
    assert "nodes-digits-total-mem" in source


def test_nodes_distribution_panel_exposes_units_dropdown() -> None:
    """Node distribution summary should expose unit select dropdown."""
    source = inspect.getsource(ClusterScreen.compose)
    assert "_NODE_DISTRIBUTION_UNITS_SELECT_ID" in source


def test_nodes_distribution_totals_default_units_are_m_and_gi() -> None:
    """Node totals formatter should default to m/Gi units."""
    screen = ClusterScreen()
    cpu_value, memory_value = screen._format_node_distribution_totals(
        1500,
        2 * (1024 ** 3),
    )
    assert cpu_value == "1500m"
    assert memory_value == "2Gi"


def test_nodes_distribution_totals_core_gb_units_conversion() -> None:
    """Node totals formatter should support core/GB conversion mode."""
    screen = ClusterScreen()
    screen._node_distribution_unit_mode = screen._NODE_DISTRIBUTION_UNIT_MODE_CORE_GB
    cpu_value, memory_value = screen._format_node_distribution_totals(
        1500,
        2 * (1024 ** 3),
    )
    assert cpu_value == "1.5core"
    assert memory_value == "2.1GB"


def test_nodes_distribution_unit_mode_setter_updates_mode() -> None:
    """Node distribution unit mode setter should switch between allowed values."""
    screen = ClusterScreen()
    assert (
        screen._node_distribution_unit_mode
        == screen._NODE_DISTRIBUTION_UNIT_MODE_MILLI_GI
    )
    screen._set_node_distribution_units_mode(
        screen._NODE_DISTRIBUTION_UNIT_MODE_CORE_GB
    )
    assert (
        screen._node_distribution_unit_mode
        == screen._NODE_DISTRIBUTION_UNIT_MODE_CORE_GB
    )


def test_workloads_pod_stats_widgets_render_req_and_limit_separately() -> None:
    """Pod stats updater should update request and limit as separate digits widgets."""
    source = inspect.getsource(ClusterScreen._update_overview_pod_stats_widgets)
    assert "_pair_value" not in source
    assert "overview-pod-cpu-req-min" in source
    assert "overview-pod-cpu-lim-min" in source
    assert "overview-pod-mem-req-p95" in source
    assert "overview-pod-mem-lim-p95" in source


def test_workloads_pod_stats_pair_labels_use_request_text() -> None:
    """Paired pod stats should show Request label instead of Req."""
    source = inspect.getsource(ClusterScreen._compose_summary_digit_pair_item)
    assert '"Request"' in source
    assert '"Limit"' in source


def test_workloads_pod_stats_default_units_are_m_and_mi() -> None:
    """Pod stats formatter should default to m/Mi units."""
    screen = ClusterScreen()
    assert screen._format_pod_stats_value("1500", metric="cpu") == "1.5km"
    assert screen._format_pod_stats_value("2048", metric="memory") == "2.048kMi"


def test_workloads_pod_stats_core_gb_units_conversion() -> None:
    """Pod stats formatter should support core/GB conversion mode."""
    screen = ClusterScreen()
    screen._pod_stats_unit_mode = screen._POD_STATS_UNIT_MODE_CORE_GB
    assert screen._format_pod_stats_value("1500", metric="cpu") == "1.5core"
    assert screen._format_pod_stats_value("2048", metric="memory") == "2gb"


def test_workloads_pod_stats_unit_mode_setter_updates_mode() -> None:
    """Pod stats unit mode setter should switch between allowed values."""
    screen = ClusterScreen()
    assert screen._pod_stats_unit_mode == screen._POD_STATS_UNIT_MODE_MILLI
    screen._set_pod_stats_units_mode(screen._POD_STATS_UNIT_MODE_CORE_GB)
    assert screen._pod_stats_unit_mode == screen._POD_STATS_UNIT_MODE_CORE_GB


def test_cluster_digits_lookup_handles_wrong_type_nodes() -> None:
    """Digits cache lookup should suppress WrongType for static-backed metrics."""
    source = inspect.getsource(ClusterScreen._get_cached_digits)
    assert "WrongType" in source


def test_cluster_top_bar_places_events_select_left_of_refresh_button() -> None:
    """Top controls should keep events selector left of refresh button."""
    source = inspect.getsource(ClusterScreen.compose)
    assert "cluster-top-controls-left" in source
    assert source.index("id=_EVENT_WINDOW_SELECT_ID") < source.index('id="refresh-btn"')


def test_cluster_top_bar_places_controls_before_loading_block() -> None:
    """Top controls should render first, with loading block occupying the right side."""
    source = inspect.getsource(ClusterScreen.compose)
    assert source.index('id="cluster-top-controls-left"') < source.index('id="cluster-loading-bar"')


def test_cluster_has_explicit_refresh_button_handler() -> None:
    """Refresh button must call action_refresh on click/press."""
    pressed_source = inspect.getsource(ClusterScreen._on_refresh_button_pressed)
    click_source = inspect.getsource(ClusterScreen.on_custom_button_clicked)
    assert "#refresh-btn" in pressed_source
    assert "action_refresh" in pressed_source
    assert "refresh-btn" in click_source
    assert "action_refresh" in click_source


def test_cluster_medium_refresh_label_is_refresh() -> None:
    """Medium-width mode should keep top button label as Refresh."""
    assert ClusterScreen._REFRESH_BUTTON_LABELS["medium"] == "Refresh"


def test_cluster_event_window_dropdown_uses_event_window_label() -> None:
    """Event lookback selector should use Event Window label in regular widths."""
    screen = ClusterScreen()
    assert screen._EVENT_WINDOW_PREFIX_BY_MODE["medium"] == "Event Window:"
    labels = [label for label, _ in screen._event_window_select_options("medium")]
    assert labels
    assert all(label.startswith("Event Window:") for label in labels)


def test_cluster_loading_bar_places_progress_text_on_right_of_progress_bar() -> None:
    """Compose order should render a 1x2 pair: progress bar then loading text."""
    source = inspect.getsource(ClusterScreen.compose)
    assert source.index('id="cluster-loading-spacer"') < source.index('id="cluster-progress-container"')
    assert source.index('id="cluster-progress-bar"') < source.index('id="loading-text"')


def test_cluster_loading_text_uses_generic_loading_label_during_progress() -> None:
    """Progress text should include percent plus generic loading label."""
    source = inspect.getsource(ClusterScreen._set_cluster_progress)
    assert 'displayed = f"{safe_percent}% Loading..."' in source


def test_cluster_inline_loading_toggle_keeps_top_bar_slot_stable() -> None:
    """Loading toggle should not hide the right-side slot container."""
    source = inspect.getsource(ClusterScreen._set_inline_loading_bars_visible)
    assert 'query_one("#cluster-loading-bar", CustomHorizontal).display = True' in source
    assert 'query_one("#cluster-progress-container", CustomHorizontal).display = visible' in source


def test_cluster_summary_digits_keep_pulse_indicator_on_update() -> None:
    """Summary digits should still show pulse marker while value is changing."""
    source = inspect.getsource(ClusterScreen._update_summary_digits_widget)
    assert 'indicator.update("●")' in source


def test_cluster_nodes_totals_use_compaction_for_readable_layout() -> None:
    """Node total CPU/mem digits should use compact formatting like other digits."""
    source = inspect.getsource(ClusterScreen._update_summary_digits_widget)
    assert 'widget_id.startswith("overview-pod-")' in source
    assert '"nodes-digits-total-cpu"' not in source
    assert '"nodes-digits-total-mem"' not in source


def test_cluster_summary_digits_clear_indicator_after_update() -> None:
    """Summary digits should clear the pulse marker after updates complete."""
    source = inspect.getsource(ClusterScreen._update_summary_digits_widget)
    assert "_SUMMARY_DIGIT_STATUS_EMOJI" not in source
    assert 'indicator.update(" ")' in source


def test_cluster_compact_digits_value_strips_warning_markup() -> None:
    """Digits values should strip warning markup decorations from formatted text."""
    screen = ClusterScreen()
    assert screen._compact_digits_value("[bold #ff9f0a]90%[/bold #ff9f0a]") == "90%"


def test_cluster_compact_digits_value_strips_critical_markup() -> None:
    """Digits values should strip critical markup decorations from formatted text."""
    screen = ClusterScreen()
    assert screen._compact_digits_value("[bold #ff3b30]111%[/bold #ff3b30]") == "111%"


def test_cluster_compact_digits_value_compacts_req_limit_pairs() -> None:
    """Req/limit pair values should compact each side and render with '/' separator."""
    screen = ClusterScreen()
    assert screen._compact_digits_value("500/1500") == "500/1.5k"
    assert screen._compact_digits_value("1500:2000") == "1.5k/2k"


def test_cluster_compact_digits_value_compacts_from_one_thousand() -> None:
    """Values at or above 1000 should compact using k/M suffixes."""
    screen = ClusterScreen()
    assert screen._compact_digits_value("999") == "999"
    assert screen._compact_digits_value("1000") == "1k"


def test_cluster_compact_digits_value_compacts_unit_suffix_values() -> None:
    """Numeric values with units should compact and preserve their unit suffix."""
    screen = ClusterScreen()
    assert screen._compact_digits_value("1200m") == "1.2km"
    assert screen._compact_digits_value("4096Mi") == "4.1kMi"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cluster_refresh_button_click_triggers_action_refresh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Clicking top-bar refresh button should invoke action_refresh."""
    screen = ClusterScreen()
    refresh_called = False

    def _fake_action_refresh() -> None:
        nonlocal refresh_called
        refresh_called = True

    monkeypatch.setattr(screen, "action_refresh", _fake_action_refresh)

    class _ClusterScreenHarnessApp(App[None]):
        def __init__(self, mounted_screen: ClusterScreen) -> None:
            super().__init__()
            self._mounted_screen = mounted_screen
            self.skip_eks = True

        def on_mount(self) -> None:
            self.push_screen(self._mounted_screen)

    app = _ClusterScreenHarnessApp(screen)
    async with app.run_test(size=(160, 44)) as pilot:
        await pilot.pause()
        await pilot.click("#refresh-btn")
        await pilot.pause()

    assert refresh_called


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cluster_resume_reapplies_responsive_height_classes() -> None:
    """Returning to Cluster should re-sync tab responsive height classes."""
    screen = ClusterScreen()

    class _ClusterScreenHarnessApp(App[None]):
        def __init__(self, mounted_screen: ClusterScreen) -> None:
            super().__init__()
            self._mounted_screen = mounted_screen
            self.skip_eks = True

        def on_mount(self) -> None:
            self.push_screen(self._mounted_screen)

    app = _ClusterScreenHarnessApp(screen)
    async with app.run_test(size=(160, 44)) as pilot:
        await pilot.pause()

        for tab_id in ("#tab-nodes", "#tab-pods", "#tab-events"):
            tab = screen.query_one(tab_id)
            tab.remove_class("height-tall", "height-short", "height-tight")
            tab.add_class("height-tight")

        screen._tab_labels_compact = True
        screen._tab_controls_layout_mode = "medium"
        screen._tab_height_layout_mode = "tight"

        screen.on_screen_resume()
        await pilot.pause()

        for tab_id in ("#tab-nodes", "#tab-pods", "#tab-events"):
            tab = screen.query_one(tab_id)
            assert "height-tall" in tab.classes
            assert "height-tight" not in tab.classes


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cluster_120x49_applies_narrow_classes_and_compact_top_controls() -> None:
    """120x49 terminals should use narrow classes and compact top controls."""
    screen = ClusterScreen()

    class _ClusterScreenHarnessApp(App[None]):
        def __init__(self, mounted_screen: ClusterScreen) -> None:
            super().__init__()
            self._mounted_screen = mounted_screen
            self.skip_eks = True

        def on_mount(self) -> None:
            self.push_screen(self._mounted_screen)

    app = _ClusterScreenHarnessApp(screen)
    async with app.run_test(size=(120, 49)) as pilot:
        await pilot.pause(0.2)

        assert screen._get_tab_controls_layout_mode() == "narrow"
        assert screen.query_one("#refresh-btn", CustomButton).label == "R"

        for tab_id in ("#tab-nodes", "#tab-pods", "#tab-events"):
            tab = screen.query_one(tab_id)
            assert "narrow" in tab.classes

        search_bar = screen.query_one("#cluster-search-bar")
        loading_bar = screen.query_one("#cluster-loading-bar")
        assert "narrow" in search_bar.classes
        assert "narrow" in loading_bar.classes

        option_labels = [label for label, _ in screen._event_window_select_options("narrow")]
        assert option_labels
        assert all(not label.startswith("Events:") for label in option_labels)
