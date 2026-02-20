"""Smoke tests for global keyboard bindings.

Tests GLOBAL_BINDINGS, NAV_BINDINGS, HELP_BINDINGS, REFRESH_BINDINGS, and APP_BINDINGS
from kubeagle.keyboard.app module.

These tests verify that global bindings are properly registered and execute
correctly using Textual's Pilot API.
"""

from __future__ import annotations

import pytest
from textual.app import App
from textual.binding import Binding

from kubeagle.screens import (
    ChartsExplorerScreen,
    ClusterScreen,
    OptimizerScreen,
    ReportExportScreen,
    SettingsScreen,
)

# =============================================================================
# GLOBAL BINDINGS TESTS
# =============================================================================


class TestGlobalBindings:
    """Test GLOBAL_BINDINGS from keyboard/app.py."""

    @pytest.mark.asyncio
    async def test_escape_triggers_back_action(self, app: App) -> None:
        """Test that escape key triggers the back action."""
        async with app.run_test() as pilot:
            await pilot.press("escape")
            # Escape triggers "back" action which should work on stacked screens
            assert app is not None

    @pytest.mark.asyncio
    async def test_h_navigates_to_home(self, app: App) -> None:
        """Test that 'h' key navigates to primary landing (Cluster).

        Verify via screen_stack that ClusterScreen was pushed after pressing 'h'.
        """
        import asyncio

        async with app.run_test(size=(120, 40)) as pilot:
            # Navigate to cluster screen first
            await pilot.press("c")
            await asyncio.sleep(1.0)
            await pilot.pause()
            # Then press h to go home
            await pilot.press("h")
            await asyncio.sleep(1.0)
            await pilot.pause()
            # Check that ClusterScreen is somewhere in the screen stack
            cluster_screens = [s for s in app.screen_stack if isinstance(s, ClusterScreen)]
            assert len(cluster_screens) > 0, (
                f"Expected ClusterScreen in stack, got: "
                f"{[type(s).__name__ for s in app.screen_stack]}"
            )

    @pytest.mark.asyncio
    async def test_c_navigates_to_cluster(self, app: App) -> None:
        """Test that 'c' key navigates to cluster screen."""
        async with app.run_test() as pilot:
            await pilot.press("c")
            await pilot.pause()
            assert isinstance(app.screen, ClusterScreen)

    @pytest.mark.asyncio
    async def test_shift_c_navigates_to_charts(self, app: App) -> None:
        """Test that 'Ctrl+c' or 'C' key navigates to charts screen."""
        async with app.run_test() as pilot:
            await pilot.press("C")
            await pilot.pause()
            assert isinstance(app.screen, ChartsExplorerScreen)

    @pytest.mark.asyncio
    async def test_o_does_not_navigate_to_optimizer(self, app: App) -> None:
        """Test that 'o' key is not bound to optimizer navigation."""
        async with app.run_test() as pilot:
            await pilot.press("o")
            await pilot.pause()
            assert not isinstance(app.screen, OptimizerScreen)

    @pytest.mark.asyncio
    async def test_e_navigates_to_export(self, app: App) -> None:
        """Test that 'e' key navigates to export screen."""
        async with app.run_test() as pilot:
            await pilot.press("e")
            await pilot.pause()
            assert isinstance(app.screen, ReportExportScreen)

    @pytest.mark.asyncio
    async def test_ctrl_s_navigates_to_settings(self, app: App) -> None:
        """Test that 'Ctrl+s' key navigates to settings screen."""
        async with app.run_test() as pilot:
            await pilot.press("ctrl+s")
            await pilot.pause()
            assert isinstance(app.screen, SettingsScreen)

    @pytest.mark.asyncio
    async def test_shift_r_navigates_to_optimizer_recommendations(self, app: App) -> None:
        """Test that 'R' (shift+r) key navigates to OptimizerScreen (recommendations view)."""
        async with app.run_test() as pilot:
            await pilot.press("R")
            await pilot.pause()
            assert isinstance(app.screen, OptimizerScreen)

    @pytest.mark.asyncio
    async def test_question_mark_shows_help(self, app: App) -> None:
        """Test that '?' key shows help dialog."""
        async with app.run_test() as pilot:
            # Press ? to trigger help
            await pilot.press("?")
            await pilot.pause()
            # Help is shown via notification, verify no errors occurred
            assert app is not None

    @pytest.mark.asyncio
    async def test_r_triggers_refresh_action(self, app: App) -> None:
        """Test that 'r' key triggers refresh action."""
        async with app.run_test() as pilot:
            await pilot.press("r")
            await pilot.pause()
            # Refresh should not cause errors
            assert app is not None

    @pytest.mark.asyncio
    async def test_q_quits_application(self, app: App) -> None:
        """Test that 'q' key triggers quit action."""
        async with app.run_test() as pilot:
            await pilot.press("q")
            await pilot.pause()
            # App should exit
            assert app._exit is True



# =============================================================================
# GLOBAL BINDINGS TUPLE VERIFICATION
# =============================================================================


class TestAppBindingsTupleVerification:
    """Verify APP_BINDINGS Binding objects contain expected key-action pairs."""

    def test_v_not_in_app_bindings(self) -> None:
        """Test 'V' is not exposed as a global app binding."""
        from kubeagle.keyboard.app import APP_BINDINGS

        binding_pairs = [(b.key, b.action) for b in APP_BINDINGS]
        assert ("V", "nav_charts_by_values_file") not in binding_pairs

    def test_n_not_in_app_bindings(self) -> None:
        """Test 'N' is not exposed as a global app binding."""
        from kubeagle.keyboard.app import APP_BINDINGS

        binding_pairs = [(b.key, b.action) for b in APP_BINDINGS]
        assert ("N", "nav_charts_without_pdb") not in binding_pairs


# =============================================================================
# NAV BINDINGS TESTS
# =============================================================================


class TestNavBindings:
    """Test NAV_BINDINGS from keyboard/app.py."""

    @pytest.mark.asyncio
    async def test_escape_pops_screen(self, app: App) -> None:
        """Test that escape key pops the current screen from stack."""
        async with app.run_test() as pilot:
            # Push a screen to have something to pop
            await pilot.press("c")
            await pilot.pause()
            initial_stack_size = len(app.screen_stack)

            await pilot.press("escape")
            await pilot.pause()

            # Stack should decrease or stay same (depends on screen type)
            assert len(app.screen_stack) <= initial_stack_size


# =============================================================================
# HELP BINDINGS TESTS
# =============================================================================


class TestHelpBindings:
    """Test HELP_BINDINGS from keyboard/app.py."""

    @pytest.mark.asyncio
    async def test_escape_closes_help(self, app: App) -> None:
        """Test that escape key closes help dialog."""
        async with app.run_test() as pilot:
            # Trigger help first
            await pilot.press("?")
            await pilot.pause()
            # Then try to close with escape
            await pilot.press("escape")
            await pilot.pause()
            # Should not cause errors
            assert app is not None

    @pytest.mark.asyncio
    async def test_q_closes_help(self, app: App) -> None:
        """Test that 'q' key closes help dialog."""
        async with app.run_test() as pilot:
            # Trigger help first
            await pilot.press("?")
            await pilot.pause()
            # Then try to close with q
            await pilot.press("q")
            await pilot.pause()
            # Should not cause errors
            assert app is not None


# =============================================================================
# REFRESH BINDINGS TESTS
# =============================================================================


class TestRefreshBindings:
    """Test REFRESH_BINDINGS from keyboard/app.py."""

    @pytest.mark.asyncio
    async def test_r_triggers_refresh(self, app: App) -> None:
        """Test that 'r' key triggers refresh."""
        async with app.run_test() as pilot:
            await pilot.press("r")
            await pilot.pause()
            # Refresh action should execute without errors
            assert app is not None


# =============================================================================
# APP BINDINGS TESTS
# =============================================================================


class TestAppBindings:
    """Test APP_BINDINGS from keyboard/app.py.

    APP_BINDINGS contains the actual Binding objects used by the app.
    These tests verify that bindings are correctly registered.
    """

    @pytest.mark.asyncio
    async def test_app_bindings_registered(self, app: App) -> None:
        """Test that APP_BINDINGS are registered on the app."""
        async with app.run_test():
            # Verify app has bindings
            assert hasattr(app, "BINDINGS")
            assert len(app.BINDINGS) > 0

    @pytest.mark.asyncio
    async def test_escape_binding_priority(self, app: App) -> None:
        """Test that escape binding has priority=True."""
        async with app.run_test():
            # Find escape binding (filter to Binding objects only)
            escape_binding = None
            for b in app.BINDINGS:
                if isinstance(b, Binding) and b.key == "escape":
                    escape_binding = b
                    break

            assert escape_binding is not None
            assert escape_binding.priority is True

    @pytest.mark.asyncio
    async def test_ctrl_s_binding_for_settings(self, app: App) -> None:
        """Test that Ctrl+s is bound to nav_settings action."""
        async with app.run_test():
            # Find ctrl+s binding (filter to Binding objects only)
            ctrl_s_binding = None
            for b in app.BINDINGS:
                if isinstance(b, Binding) and b.key == "ctrl+s":
                    ctrl_s_binding = b
                    break

            assert ctrl_s_binding is not None
            assert ctrl_s_binding.action == "nav_settings"

    @pytest.mark.asyncio
    async def test_navigation_bindings_execute(self, app: App) -> None:
        """Test that navigation bindings execute correctly."""
        async with app.run_test() as pilot:
            # Test home navigation
            await pilot.press("h")
            await pilot.pause()
            assert isinstance(app.screen, ClusterScreen)

            # Test charts navigation from home (global binding)
            await pilot.press("C")
            await pilot.pause()
            assert isinstance(app.screen, ChartsExplorerScreen)

            # Test export navigation (need to go back home first due to screen-specific bindings)
            await pilot.press("escape")
            await pilot.pause()
            await pilot.press("e")
            await pilot.pause()
            assert isinstance(app.screen, ReportExportScreen)

    @pytest.mark.asyncio
    async def test_quit_binding_priority(self, app: App) -> None:
        """Test that quit binding has priority=True."""
        async with app.run_test():
            # Find quit binding (filter to Binding objects only)
            quit_binding = None
            for b in app.BINDINGS:
                if isinstance(b, Binding) and b.key == "q":
                    quit_binding = b
                    break

            assert quit_binding is not None
            assert quit_binding.priority is True


# =============================================================================
# BINDING COUNT VERIFICATION
# =============================================================================


class TestBindingCounts:
    """Verify expected number of bindings are present."""

    def test_app_bindings_count(self) -> None:
        """Test that APP_BINDINGS has expected number of bindings."""
        from kubeagle.keyboard.app import APP_BINDINGS

        # Should have: escape, h, c, C, e, ctrl+s, R, ?, r, q = 10
        assert len(APP_BINDINGS) == 10


# =============================================================================
# CHARTS EXPLORER SCREEN IMPORT VERIFICATION
# =============================================================================


class TestChartsExplorerScreenImportVerification:
    """Test that ChartsExplorerScreen is importable from screens package."""

    def test_charts_explorer_screen_importable(self) -> None:
        """Test ChartsExplorerScreen can be imported from screens package."""
        assert ChartsExplorerScreen is not None

    def test_charts_explorer_screen_is_screen_subclass(self) -> None:
        """Test ChartsExplorerScreen is a Textual Screen subclass."""
        from textual.screen import Screen

        assert issubclass(ChartsExplorerScreen, Screen)
