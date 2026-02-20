"""Unit tests for Charts Explorer summary KPI formatting."""

from __future__ import annotations

import pytest

from kubeagle.screens.charts_explorer.charts_explorer_screen import (
    ChartsExplorerScreen,
)


class _FakeKPI:
    def __init__(self) -> None:
        self.value = ""

    def set_value(self, value: str) -> None:
        self.value = value


@pytest.mark.unit
def test_update_summary_shows_percentages_for_chart_legends(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """KPI legend values should include percentages based on filtered charts."""
    screen = ChartsExplorerScreen(testing=True)
    widgets = {
        "#kpi-total": _FakeKPI(),
        "#kpi-extreme": _FakeKPI(),
        "#kpi-single": _FakeKPI(),
        "#kpi-no-pdb": _FakeKPI(),
    }

    def _query_one(selector: str, *_args: object, **_kwargs: object) -> _FakeKPI:
        return widgets[selector]

    monkeypatch.setattr(screen, "query_one", _query_one)
    monkeypatch.setattr(
        screen._presenter,
        "build_summary_metrics",
        lambda _all, _filtered: {
            "shown": 8,
            "total": 10,
            "filtered_extreme": 3,
            "filtered_single_replica": 2,
            "filtered_no_pdb": 1,
        },
    )

    screen._update_summary()

    assert widgets["#kpi-total"].value == "8/10 (80%)"
    assert widgets["#kpi-extreme"].value == "3 (38%)"
    assert widgets["#kpi-single"].value == "2 (25%)"
    assert widgets["#kpi-no-pdb"].value == "1 (12%)"


@pytest.mark.unit
def test_update_summary_handles_zero_filtered_charts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No filtered charts should display 0% for category legends."""
    screen = ChartsExplorerScreen(testing=True)
    widgets = {
        "#kpi-total": _FakeKPI(),
        "#kpi-extreme": _FakeKPI(),
        "#kpi-single": _FakeKPI(),
        "#kpi-no-pdb": _FakeKPI(),
    }

    def _query_one(selector: str, *_args: object, **_kwargs: object) -> _FakeKPI:
        return widgets[selector]

    monkeypatch.setattr(screen, "query_one", _query_one)
    monkeypatch.setattr(
        screen._presenter,
        "build_summary_metrics",
        lambda _all, _filtered: {
            "shown": 0,
            "total": 10,
            "filtered_extreme": 0,
            "filtered_single_replica": 0,
            "filtered_no_pdb": 0,
        },
    )

    screen._update_summary()

    assert widgets["#kpi-total"].value == "0/10 (0%)"
    assert widgets["#kpi-extreme"].value == "0 (0%)"
    assert widgets["#kpi-single"].value == "0 (0%)"
    assert widgets["#kpi-no-pdb"].value == "0 (0%)"
