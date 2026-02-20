"""Unit tests for non-blocking cluster table overlays during refresh."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from kubeagle.screens.cluster.cluster_screen import ClusterScreen


def _patch_refresh_side_effects(
    screen: ClusterScreen,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[dict[str, bool], dict[str, bool], list[bool]]:
    tab_overlay_calls: dict[str, bool] = {}
    table_overlay_calls: dict[str, bool] = {}
    load_data_calls: list[bool] = []

    monkeypatch.setattr(
        ClusterScreen,
        "app",
        property(lambda _self: SimpleNamespace(skip_eks=False)),
    )
    monkeypatch.setattr(screen, "_set_inline_loading_bars_visible", lambda _visible: None)
    monkeypatch.setattr(
        screen,
        "_set_cluster_progress",
        lambda _percent, _text, *, is_error=False: None,
    )
    monkeypatch.setattr(screen, "_reset_summary_widgets_for_refresh", lambda: None)
    monkeypatch.setattr(
        screen,
        "_set_tab_loading_overlay_visible",
        lambda tab_id, visible: tab_overlay_calls.__setitem__(tab_id, visible),
    )
    monkeypatch.setattr(
        screen,
        "_set_table_overlay_visible",
        lambda table_id, visible: table_overlay_calls.__setitem__(table_id, visible),
    )
    monkeypatch.setattr(
        screen,
        "_set_tab_loading_text",
        lambda _tab_id, *, label_text=None, status_text=None: None,
    )
    monkeypatch.setattr(screen, "_start_connection_stall_watchdog", lambda: None)
    monkeypatch.setattr(
        screen._presenter,
        "load_data",
        lambda *, force_refresh=False: load_data_calls.append(force_refresh),
    )
    return tab_overlay_calls, table_overlay_calls, load_data_calls


@pytest.mark.unit
def test_action_refresh_keeps_tab_and_table_overlays_hidden_when_payload_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Refresh should keep current table data interactive when prior payload is available."""
    screen = ClusterScreen()
    for key in screen._build_reverse_map():
        screen._presenter._data[key] = [{"loaded": True}]

    tab_calls, table_calls, load_calls = _patch_refresh_side_effects(screen, monkeypatch)
    screen.action_refresh()

    assert load_calls == [True]
    assert tab_calls
    assert table_calls
    assert all(not is_visible for is_visible in tab_calls.values())
    assert all(not is_visible for is_visible in table_calls.values())


@pytest.mark.unit
def test_action_refresh_shows_tab_and_table_overlays_when_payload_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cold refresh with no prior data should keep loading overlays visible."""
    screen = ClusterScreen()
    screen._presenter._data.clear()

    tab_calls, table_calls, load_calls = _patch_refresh_side_effects(screen, monkeypatch)
    screen.action_refresh()

    assert load_calls == [True]
    assert tab_calls
    assert table_calls
    assert all(is_visible for is_visible in tab_calls.values())
    assert all(is_visible for is_visible in table_calls.values())


@pytest.mark.unit
def test_charts_overview_fallback_is_not_treated_as_workloads_payload() -> None:
    """Unavailable chart KPI fallback should not suppress workloads loading overlays."""
    screen = ClusterScreen()
    screen._presenter._data["charts_overview"] = screen._presenter._default_charts_overview()

    assert screen._has_source_payload("charts_overview") is False
    assert screen._tab_has_any_payload("tab-pods") is False


@pytest.mark.unit
def test_action_refresh_keeps_workloads_overlay_visible_with_only_chart_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Workloads tab should stay in loading state when only chart fallback data exists."""
    screen = ClusterScreen()
    screen._presenter._data["charts_overview"] = screen._presenter._default_charts_overview()

    tab_calls, _table_calls, load_calls = _patch_refresh_side_effects(screen, monkeypatch)
    screen.action_refresh()

    assert load_calls == [True]
    assert tab_calls["tab-pods"] is True
