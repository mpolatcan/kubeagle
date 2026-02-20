"""Unit tests for workloads Node Analysis drill-down behavior."""

from __future__ import annotations

import inspect
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from kubeagle.models.core.workload_inventory_info import (
    WorkloadLiveUsageSampleInfo,
)
from kubeagle.screens.workloads.config import (
    TAB_WORKLOADS_NODE_ANALYSIS,
    WORKLOADS_TABLE_COLUMNS_BY_TAB,
    WORKLOADS_TABLE_ID_BY_TAB,
)
from kubeagle.screens.workloads.workloads_screen import (
    WorkloadsScreen,
    _WorkloadAssignedNodesDetailModal,
)


def test_double_select_on_node_analysis_row_opens_drilldown_modal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Selecting the same row twice quickly should open node-analysis detail modal."""
    screen = WorkloadsScreen()
    screen._active_tab_id = TAB_WORKLOADS_NODE_ANALYSIS
    table_id = WORKLOADS_TABLE_ID_BY_TAB[TAB_WORKLOADS_NODE_ANALYSIS]
    workload = SimpleNamespace(name="api", namespace="team-a", kind="Deployment")
    screen._row_workload_map_by_table = {table_id: {0: workload}}

    opened_workloads: list[object] = []
    monkeypatch.setattr(
        screen,
        "_open_node_details_modal",
        lambda selected_workload: opened_workloads.append(selected_workload),
    )
    monotonic_values = iter([100.0, 100.2])
    monkeypatch.setattr(
        "kubeagle.screens.workloads.workloads_screen.time.monotonic",
        lambda: next(monotonic_values),
    )

    event = SimpleNamespace(
        data_table=SimpleNamespace(id=table_id),
        cursor_row=0,
    )
    screen.on_data_table_row_selected(event)
    screen.on_data_table_row_selected(event)

    assert opened_workloads == [workload]


def test_single_select_does_not_open_drilldown_modal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Single select should not trigger drill-down modal."""
    screen = WorkloadsScreen()
    screen._active_tab_id = TAB_WORKLOADS_NODE_ANALYSIS
    table_id = WORKLOADS_TABLE_ID_BY_TAB[TAB_WORKLOADS_NODE_ANALYSIS]
    workload = SimpleNamespace(name="api", namespace="team-a", kind="Deployment")
    screen._row_workload_map_by_table = {table_id: {0: workload}}

    open_modal = MagicMock()
    monkeypatch.setattr(screen, "_open_node_details_modal", open_modal)
    monkeypatch.setattr(
        "kubeagle.screens.workloads.workloads_screen.time.monotonic",
        lambda: 10.0,
    )

    event = SimpleNamespace(
        data_table=SimpleNamespace(id=table_id),
        cursor_row=0,
    )
    screen.on_data_table_row_selected(event)

    open_modal.assert_not_called()


def test_open_node_details_modal_pushes_modal_with_detail_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Modal should include node and pod drill-down rows from presenter helpers."""
    screen = WorkloadsScreen()

    class _FakeApp:
        def __init__(self) -> None:
            self.pushed: list[object] = []

        def push_screen(self, modal: object) -> None:
            self.pushed.append(modal)

    fake_app = _FakeApp()
    monkeypatch.setattr(type(screen), "app", property(lambda _self: fake_app))
    node_rows = [
        (
            "node-a",
            "ng-a",
            "1",
            "70%",
            "40%",
            "60%",
            "30%",
            "1000m",
            "2.0Gi",
            "250m",
            "1.0Gi",
        )
    ]
    pod_rows = [
        (
            "team-a",
            "api-a",
            "node-a",
            "Running",
            "250m (6.2%)",
            "1.0Gi (12%)",
            "4000m",
            "8.0Gi",
            "CrashLoopBackOff",
            "137",
        )
    ]
    monkeypatch.setattr(
        screen._presenter,
        "get_assigned_node_detail_rows",
        lambda _workload: node_rows,
    )
    monkeypatch.setattr(
        screen._presenter,
        "get_assigned_pod_detail_rows",
        lambda _workload: pod_rows,
    )

    workload = SimpleNamespace(name="api", namespace="team-a", kind="Deployment")
    screen._open_node_details_modal(workload)

    assert len(fake_app.pushed) == 1
    modal = fake_app.pushed[0]
    assert isinstance(modal, _WorkloadAssignedNodesDetailModal)
    assert modal._node_rows == node_rows
    assert modal._pod_rows == pod_rows


def test_node_analysis_uses_single_configured_column_set() -> None:
    """Node-analysis should always use the single configured column preset."""
    screen = WorkloadsScreen()
    assert screen._columns_for_tab(TAB_WORKLOADS_NODE_ANALYSIS) == (
        WORKLOADS_TABLE_COLUMNS_BY_TAB[TAB_WORKLOADS_NODE_ANALYSIS]
    )


def test_node_details_modal_compose_includes_live_plot_tab() -> None:
    """Drilldown modal should expose Tables and Live Plot tab labels."""
    source = inspect.getsource(_WorkloadAssignedNodesDetailModal.compose)
    assert "Tables" in source
    assert "Live Plot" in source
    assert "workloads-node-details-cpu-plot" in source
    assert "workloads-node-details-memory-plot" in source


def test_node_details_modal_tab_change_triggers_polling_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Switching drilldown tabs should resume/pause live polling."""

    async def _provider() -> WorkloadLiveUsageSampleInfo:
        return WorkloadLiveUsageSampleInfo(
            timestamp_epoch=1.0,
            namespace="team-a",
            workload_kind="Deployment",
            workload_name="api",
        )

    modal = _WorkloadAssignedNodesDetailModal(
        workload_name="api",
        workload_namespace="team-a",
        workload_kind="Deployment",
        node_rows=[],
        pod_rows=[],
        live_sample_provider=_provider,
    )
    calls: list[str] = []
    monkeypatch.setattr(modal, "_resume_live_polling", lambda: calls.append("resume"))
    monkeypatch.setattr(modal, "_pause_live_polling", lambda: calls.append("pause"))

    modal._on_detail_tab_changed(modal._DETAIL_TAB_LIVE)
    modal._on_detail_tab_changed(modal._DETAIL_TAB_TABLES)

    assert calls == ["resume", "pause"]


def test_node_details_modal_history_caps_at_720() -> None:
    """Live history buffers should cap at configured max length."""

    async def _provider() -> WorkloadLiveUsageSampleInfo:
        return WorkloadLiveUsageSampleInfo(
            timestamp_epoch=1.0,
            namespace="team-a",
            workload_kind="Deployment",
            workload_name="api",
        )

    modal = _WorkloadAssignedNodesDetailModal(
        workload_name="api",
        workload_namespace="team-a",
        workload_kind="Deployment",
        node_rows=[],
        pod_rows=[],
        live_sample_provider=_provider,
    )
    for idx in range(modal._LIVE_HISTORY_LIMIT + 5):
        modal._live_timestamps.append(float(idx))
        modal._live_cpu_timestamps.append(float(idx))
        modal._live_cpu_values.append(float(idx))
        modal._live_memory_timestamps.append(float(idx))
        modal._live_memory_values.append(float(idx))

    assert len(modal._live_timestamps) == modal._LIVE_HISTORY_LIMIT
    assert len(modal._live_cpu_timestamps) == modal._LIVE_HISTORY_LIMIT
    assert len(modal._live_cpu_values) == modal._LIVE_HISTORY_LIMIT
    assert len(modal._live_memory_timestamps) == modal._LIVE_HISTORY_LIMIT
    assert len(modal._live_memory_values) == modal._LIVE_HISTORY_LIMIT


def test_node_details_modal_enqueue_triggers_animation_start_when_idle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Enqueueing a sample while idle should trigger animation startup."""

    async def _provider() -> WorkloadLiveUsageSampleInfo:
        return WorkloadLiveUsageSampleInfo(
            timestamp_epoch=1.0,
            namespace="team-a",
            workload_kind="Deployment",
            workload_name="api",
        )

    modal = _WorkloadAssignedNodesDetailModal(
        workload_name="api",
        workload_namespace="team-a",
        workload_kind="Deployment",
        node_rows=[],
        pod_rows=[],
        live_sample_provider=_provider,
    )
    started: list[str] = []
    monkeypatch.setattr(
        modal,
        "_start_next_live_animation",
        lambda: started.append("start"),
    )

    sample = WorkloadLiveUsageSampleInfo(
        timestamp_epoch=10.0,
        namespace="team-a",
        workload_kind="Deployment",
        workload_name="api",
        workload_cpu_mcores=120.0,
        workload_memory_bytes=256.0,
    )
    modal._enqueue_live_sample_for_animation(sample)

    assert len(modal._live_animation_queue) == 1
    assert started == ["start"]


def test_node_details_modal_commit_active_animation_sample_updates_history() -> None:
    """Committing an active animated sample should persist final history points."""

    async def _provider() -> WorkloadLiveUsageSampleInfo:
        return WorkloadLiveUsageSampleInfo(
            timestamp_epoch=1.0,
            namespace="team-a",
            workload_kind="Deployment",
            workload_name="api",
        )

    modal = _WorkloadAssignedNodesDetailModal(
        workload_name="api",
        workload_namespace="team-a",
        workload_kind="Deployment",
        node_rows=[],
        pod_rows=[],
        live_sample_provider=_provider,
    )
    modal._live_animation_active = WorkloadLiveUsageSampleInfo(
        timestamp_epoch=25.0,
        namespace="team-a",
        workload_kind="Deployment",
        workload_name="api",
        workload_cpu_mcores=333.0,
        workload_memory_bytes=777.0,
    )

    modal._commit_active_animation_sample()

    assert modal._live_timestamps[-1] == 25.0
    assert modal._live_cpu_timestamps[-1] == 25.0
    assert modal._live_cpu_values[-1] == 333.0
    assert modal._live_memory_timestamps[-1] == 25.0
    assert modal._live_memory_values[-1] == 777.0


def test_node_details_modal_stops_polling_on_cancel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cancel action should stop polling before dismissing."""

    async def _provider() -> WorkloadLiveUsageSampleInfo:
        return WorkloadLiveUsageSampleInfo(
            timestamp_epoch=1.0,
            namespace="team-a",
            workload_kind="Deployment",
            workload_name="api",
        )

    modal = _WorkloadAssignedNodesDetailModal(
        workload_name="api",
        workload_namespace="team-a",
        workload_kind="Deployment",
        node_rows=[],
        pod_rows=[],
        live_sample_provider=_provider,
    )
    stop_polling = MagicMock()
    monkeypatch.setattr(modal, "_stop_live_polling", stop_polling)
    monkeypatch.setattr(modal, "dismiss", lambda _result: None)

    modal.action_cancel()

    stop_polling.assert_called_once()
