"""Unit tests for ClusterScreen connection-stall watchdog behavior."""

from __future__ import annotations

import time
from types import SimpleNamespace

from textual.message import Message

from kubeagle.screens.cluster.cluster_screen import ClusterScreen
from kubeagle.screens.cluster.presenter import ClusterDataLoadFailed


class _WatchdogClusterScreen(ClusterScreen):
    """ClusterScreen test double that captures watchdog side effects."""

    def __init__(self) -> None:
        super().__init__()
        self.progress_updates: list[tuple[int, str, bool]] = []
        self.posted_messages: list[Message] = []
        self.cancelled_workers = 0

    @property
    def is_current(self) -> bool:
        return True

    @property
    def workers(self) -> SimpleNamespace:
        return SimpleNamespace(cancel_all=self._cancel_workers)

    def _cancel_workers(self) -> None:
        self.cancelled_workers += 1

    def _set_cluster_progress(
        self, percent: int, state_text: str, *, is_error: bool = False
    ) -> None:
        self._cluster_load_progress = percent
        self.progress_updates.append((percent, state_text, is_error))

    def post_message(self, message: Message) -> bool:
        self.posted_messages.append(message)
        return True


def test_connection_stall_watchdog_warns_before_timeout() -> None:
    """Watchdog should show a slow-connection hint before hard timeout."""
    screen = _WatchdogClusterScreen()
    screen._presenter._is_loading = True
    screen._loading_message = "Checking cluster connection..."
    screen._cluster_load_progress = 5
    screen._connection_phase_started_at = (
        time.monotonic() - screen._CONNECTION_STALL_WARN_SECONDS - 0.5
    )

    screen._check_connection_stall()

    assert screen.posted_messages == []
    assert screen.progress_updates
    _, state_text, _ = screen.progress_updates[-1]
    assert "slow" in state_text.lower()


def test_connection_stall_watchdog_fails_after_timeout() -> None:
    """Watchdog should fail and post an actionable error after timeout."""
    screen = _WatchdogClusterScreen()
    screen._presenter._is_loading = True
    screen._loading_message = "Checking cluster connection..."
    screen._cluster_load_progress = 5
    screen._connection_phase_started_at = (
        time.monotonic() - screen._CONNECTION_STALL_FAIL_SECONDS - 0.5
    )

    screen._check_connection_stall()

    assert screen.cancelled_workers == 1
    assert len(screen.posted_messages) == 1
    failure = screen.posted_messages[0]
    assert isinstance(failure, ClusterDataLoadFailed)
    assert "timed out" in failure.error.lower()


def test_connection_stall_watchdog_ignores_non_connection_messages() -> None:
    """Watchdog should not trigger on normal data-loading progress phases."""
    screen = _WatchdogClusterScreen()
    screen._presenter._is_loading = True
    screen._loading_message = "Loading data (2/20)..."
    screen._cluster_load_progress = 20
    screen._connection_phase_started_at = (
        time.monotonic() - screen._CONNECTION_STALL_FAIL_SECONDS - 0.5
    )

    screen._check_connection_stall()

    assert screen.posted_messages == []
    assert screen.progress_updates == []
    assert screen.cancelled_workers == 0
    assert screen._connection_phase_started_at is None


def test_connection_stall_watchdog_surfaces_interrupted_load() -> None:
    """If loading stops early without success/failure, show retry guidance."""
    screen = _WatchdogClusterScreen()
    screen._presenter._is_loading = False
    screen._data_loaded = False
    screen._error_message = None
    screen._loading_message = "Checking cluster connection..."
    screen._cluster_load_progress = 5
    screen._connection_phase_started_at = (
        time.monotonic() - screen._LOAD_INTERRUPTED_GRACE_SECONDS - 0.5
    )

    screen._check_connection_stall()

    assert len(screen.posted_messages) == 1
    failure = screen.posted_messages[0]
    assert isinstance(failure, ClusterDataLoadFailed)
    assert "interrupted" in failure.error.lower()


def test_normalize_loading_message_preserves_fetch_status_suffix() -> None:
    """Loading messages should keep active-source status text when present."""
    screen = ClusterScreen()

    message = "Loading data (3/18)... Fetching: Nodes, Events"
    normalized = screen._normalize_loading_message(message)

    assert normalized == "Fetching: Nodes, Events"
    assert screen._progress_from_message(message) > 0


def test_partial_progress_keeps_latest_fetch_status_text() -> None:
    """Partial source updates should not overwrite active fetch status text."""
    screen = _WatchdogClusterScreen()
    screen._presenter._is_loading = True
    screen._presenter._loaded_keys = {"nodes", "events"}
    screen._progress_seen_source_keys = {"nodes", "events"}
    screen._loading_message = "Fetching: Nodes, Events"
    screen._cluster_load_progress = 20

    screen._update_partial_load_progress()

    assert screen.progress_updates
    _, state_text, is_error = screen.progress_updates[-1]
    assert state_text == "Fetching: Nodes, Events"
    assert is_error is False


def test_partial_progress_advances_from_streamed_sources_before_completion() -> None:
    """Streamed source notifications should move progress above the connection baseline."""
    screen = _WatchdogClusterScreen()
    screen._presenter._is_loading = True
    screen._presenter._loaded_keys = set()
    screen._progress_seen_source_keys = {"nodes"}
    screen._loading_message = "Loading data (0/18)... Fetching: Nodes"
    screen._cluster_load_progress = 5

    screen._update_partial_load_progress()

    assert screen.progress_updates
    percent, _state_text, _is_error = screen.progress_updates[-1]
    assert percent > 5


def test_sync_tab_filter_options_throttles_signature_rebuild_while_loading(
    monkeypatch,
) -> None:
    """Loading bursts should skip expensive filter signature recomputation."""
    screen = ClusterScreen()
    screen._presenter._is_loading = True
    screen._tab_filter_source_signatures["tab-nodes"] = 123
    screen._tab_filter_last_sync_at["tab-nodes"] = 100.0

    button_refresh_calls: list[str] = []
    monkeypatch.setattr(
        screen,
        "_update_filter_dialog_button",
        lambda tab_id: button_refresh_calls.append(tab_id),
    )
    monkeypatch.setattr(
        "kubeagle.screens.cluster.cluster_screen.time.monotonic",
        lambda: 100.1,
    )

    signature_called = False

    def _forbidden_signature(_: object) -> int:
        nonlocal signature_called
        signature_called = True
        return 0

    monkeypatch.setattr(screen, "_table_data_signature", _forbidden_signature)

    screen._sync_tab_filter_options("tab-nodes", [])

    assert button_refresh_calls == ["tab-nodes"]
    assert signature_called is False


def test_flush_source_refresh_applies_updates_without_extra_loading_delay(
    monkeypatch,
) -> None:
    """Pending source updates should repaint active tab immediately while loading."""
    screen = _WatchdogClusterScreen()
    screen._presenter._is_loading = True
    screen._data_loaded = True
    screen._pending_source_tabs = {"tab-nodes"}
    screen._pending_source_keys = {"nodes"}
    screen._last_source_refresh_at = time.monotonic()

    refreshed_tabs: list[str] = []
    deferred_schedules: list[str] = []
    monkeypatch.setattr(screen, "_get_active_tab_id", lambda: "tab-nodes")
    monkeypatch.setattr(screen, "_refresh_tab", lambda tab_id: refreshed_tabs.append(tab_id))
    monkeypatch.setattr(screen, "_update_status_bar", lambda: None)
    monkeypatch.setattr(
        screen,
        "_schedule_source_refresh",
        lambda: deferred_schedules.append("scheduled"),
    )

    screen._flush_source_refresh()

    assert refreshed_tabs == ["tab-nodes"]
    assert deferred_schedules == []
    assert screen._pending_source_tabs == set()
    assert screen._pending_source_keys == set()


def test_set_cluster_progress_keeps_refresh_animation_when_target_decreases(
    monkeypatch,
) -> None:
    """Refresh should animate percent changes instead of snapping downward."""

    class _Timer:
        def stop(self) -> None:
            return

    screen = ClusterScreen()
    screen._cluster_progress_display = 100
    screen._cluster_progress_target = 100
    started_intervals: list[float] = []
    monkeypatch.setattr(
        screen,
        "set_interval",
        lambda interval, callback: started_intervals.append(interval) or _Timer(),
    )
    monkeypatch.setattr(screen, "_render_cluster_progress", lambda: None)

    screen._set_cluster_progress(0, "Refreshing...")

    assert started_intervals
    assert screen._cluster_progress_target == 0
    assert screen._cluster_progress_display == 100
