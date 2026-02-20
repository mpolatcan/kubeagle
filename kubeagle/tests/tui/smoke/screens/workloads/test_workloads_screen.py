"""Smoke tests for dedicated WorkloadsScreen composition and wiring."""

from __future__ import annotations

import inspect

from kubeagle.keyboard import WORKLOADS_SCREEN_BINDINGS
from kubeagle.screens.workloads import WorkloadsScreen
from kubeagle.screens.workloads.config import (
    TAB_WORKLOADS_ALL,
    TAB_WORKLOADS_EXTREME_RATIOS,
    TAB_WORKLOADS_MISSING_PDB,
    TAB_WORKLOADS_NODE_ANALYSIS,
    TAB_WORKLOADS_SINGLE_REPLICA,
    WORKLOADS_TAB_IDS,
    WORKLOADS_TABLE_COLUMNS_BY_TAB,
    WORKLOADS_TABLE_ID_BY_TAB,
)


class TestWorkloadsScreenWidgetComposition:
    """WorkloadsScreen should expose dedicated workloads UI structure."""

    def test_screen_has_bindings(self) -> None:
        assert hasattr(WorkloadsScreen, "BINDINGS")
        assert len(WorkloadsScreen.BINDINGS) > 0
        assert WorkloadsScreen.BINDINGS is WORKLOADS_SCREEN_BINDINGS

    def test_bindings_cover_all_workloads_tabs(self) -> None:
        binding_pairs = [(key, action) for key, action, _ in WorkloadsScreen.BINDINGS]
        assert ("slash", "focus_search") in binding_pairs
        assert ("1", "switch_tab_1") in binding_pairs
        assert ("2", "switch_tab_2") in binding_pairs
        assert ("3", "switch_tab_3") in binding_pairs
        assert ("4", "switch_tab_4") in binding_pairs
        assert ("5", "switch_tab_5") in binding_pairs

    def test_screen_has_css_path(self) -> None:
        assert hasattr(WorkloadsScreen, "CSS_PATH")
        assert "workloads" in WorkloadsScreen.CSS_PATH.lower()

    def test_screen_can_be_instantiated(self) -> None:
        screen = WorkloadsScreen()
        assert screen is not None
        assert screen._presenter is not None

    def test_screen_has_workloads_tabs(self) -> None:
        expected_tabs = [
            TAB_WORKLOADS_ALL,
            TAB_WORKLOADS_EXTREME_RATIOS,
            TAB_WORKLOADS_SINGLE_REPLICA,
            TAB_WORKLOADS_MISSING_PDB,
            TAB_WORKLOADS_NODE_ANALYSIS,
        ]
        assert expected_tabs == WORKLOADS_TAB_IDS

    def test_compose_contains_dedicated_workloads_widgets(self) -> None:
        source = inspect.getsource(WorkloadsScreen.compose)
        assert "workloads-view-tabs" in source
        assert "workloads-node-analysis-mode-tabs" not in source
        assert "workloads-content-switcher" in source
        assert "loading-overlay" in source
        assert "loading-indicator" in source
        assert "workloads-progress-bar" in source
        assert "workloads-filter-btn" in source
        assert WORKLOADS_TABLE_ID_BY_TAB[TAB_WORKLOADS_ALL] == "workloads-all-table"
        assert (
            WORKLOADS_TABLE_ID_BY_TAB[TAB_WORKLOADS_EXTREME_RATIOS]
            == "workloads-extreme-ratios-table"
        )
        assert (
            WORKLOADS_TABLE_ID_BY_TAB[TAB_WORKLOADS_SINGLE_REPLICA]
            == "workloads-single-replica-table"
        )
        assert (
            WORKLOADS_TABLE_ID_BY_TAB[TAB_WORKLOADS_MISSING_PDB]
            == "workloads-missing-pdb-table"
        )
        assert (
            WORKLOADS_TABLE_ID_BY_TAB[TAB_WORKLOADS_NODE_ANALYSIS]
            == "workloads-node-analysis-table"
        )

    def test_tab_switch_actions_exist(self) -> None:
        screen = WorkloadsScreen()
        assert hasattr(screen, "action_switch_tab_1")
        assert hasattr(screen, "action_switch_tab_2")
        assert hasattr(screen, "action_switch_tab_3")
        assert hasattr(screen, "action_switch_tab_4")
        assert hasattr(screen, "action_switch_tab_5")

    def test_node_columns_are_scoped_to_node_analysis_tab(self) -> None:
        non_node_tabs = (
            TAB_WORKLOADS_ALL,
            TAB_WORKLOADS_EXTREME_RATIOS,
            TAB_WORKLOADS_SINGLE_REPLICA,
            TAB_WORKLOADS_MISSING_PDB,
        )
        for tab_id in non_node_tabs:
            column_names = [name for name, _ in WORKLOADS_TABLE_COLUMNS_BY_TAB[tab_id]]
            assert "Nodes" not in column_names
            assert "Node CPU Usage/Req/Lim Avg" not in column_names
            assert "Node CPU Usage/Req/Lim P95" not in column_names
            assert "Desired/Ready" not in column_names
            assert "Restarts" in column_names
            assert "PDB" in column_names

        node_tab_columns = [
            name for name, _ in WORKLOADS_TABLE_COLUMNS_BY_TAB[TAB_WORKLOADS_NODE_ANALYSIS]
        ]
        assert "Nodes" in node_tab_columns
        assert "Restarts" in node_tab_columns
        assert "PDB" not in node_tab_columns
        assert "Desired/Ready" not in node_tab_columns
        assert node_tab_columns.index("Restarts") > node_tab_columns.index("Mem R/L")
        assert "Node CPU Usage/Req/Lim Avg" in node_tab_columns
        assert "Node CPU Usage/Req/Lim P95" in node_tab_columns
        assert "Neighbor CPU Pressure Max/Avg" not in node_tab_columns
        assert "Neighbor CPU Req Pressure Max/Avg" not in node_tab_columns
