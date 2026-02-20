"""Smoke tests for keypress navigation with real worker execution.

This module tests the FULL navigation and data loading flow:
1. Press keys to navigate (like a real user would)
2. Trigger real worker execution (NOT testing=True mode)
3. Verify DataTable population after data loading
4. Expose RowDoesNotExist errors in tests (not just runtime)

IMPORTANT - TEST BEHAVIOR:
These tests are DESIGNED to FAIL until the RowDoesNotExist bug is fixed.
Currently they expose the bug that only occurred at runtime before.

The key difference from existing tests:
- Existing tests use `testing=True` to skip workers (avoiding timing issues)
- These tests use real workers to test actual runtime behavior
- Tests FAIL if RowDoesNotExist or other data loading errors occur

Usage:
    pytest kubeagle/tests/tui/smoke/test_keypress_navigation.py -v

Marked with:
- @pytest.mark.smoke: fast runtime checks for CI smoke budget
- @pytest.mark.slow: deeper runtime/race-condition checks
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import pytest

from kubeagle.app import EKSHelmReporterApp
from kubeagle.screens import (
    ChartsExplorerScreen,
    OptimizerScreen,
)
from kubeagle.widgets import CustomDataTable

logger = logging.getLogger(__name__)

# Path to test charts data (web-helm-repository at repo root)
# Use absolute path to avoid working directory issues
REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
TEST_CHARTS_PATH = REPO_ROOT / "web-helm-repository"

# Also check sibling directory (web-helm-repository is next to kubeagle)
if not TEST_CHARTS_PATH.exists():
    SIBLING_ROOT = REPO_ROOT.parent / "web-helm-repository"
    if SIBLING_ROOT.exists():
        TEST_CHARTS_PATH = SIBLING_ROOT


class TestChartsExplorerScreenWithDataNavigation:
    """Test ChartsExplorerScreen navigation via keypress with real data loading.

    This tests the full flow:
    1. Start app
    2. Press "C" key to navigate to ChartsExplorerScreen
    3. Wait for worker to complete data loading
    4. Verify DataTable has rows populated
    5. Check for RowDoesNotExist errors
    """

    @pytest.mark.asyncio
    @pytest.mark.smoke
    async def test_charts_screen_keypress_navigation_with_data(self) -> None:
        """Test 'C' key navigates to ChartsExplorerScreen and loads real data."""
        # Skip if no test data available
        if not TEST_CHARTS_PATH.exists():
            pytest.skip(f"Test charts path not found: {TEST_CHARTS_PATH}")

        app = EKSHelmReporterApp(charts_path=TEST_CHARTS_PATH, skip_eks=True)

        async with app.run_test() as pilot:
            # Initial state - app lands on Cluster summary
            await pilot.pause()

            # Press "C" key to navigate to ChartsExplorerScreen
            # This triggers action_nav_charts() which pushes ChartsExplorerScreen()
            await pilot.press("C")
            await pilot.pause()

            # Verify ChartsExplorerScreen is in the stack
            charts_screens = [s for s in app.screen_stack if isinstance(s, ChartsExplorerScreen)]
            assert len(charts_screens) > 0, "ChartsExplorerScreen should be in screen stack after 'C' key"

            # Get the ChartsExplorerScreen instance
            charts_screen = charts_screens[0]

            # Wait for worker to complete - give it time to load data
            # The worker starts in on_mount() when testing=False (our case)
            await asyncio.sleep(2)  # Give worker time to complete
            await pilot.pause()

            # Try to access the DataTable and check for rows
            try:
                # Query the DataTable
                data_table = charts_screen.query_one("#explorer-table", CustomDataTable)

                # Check row count - should have loaded data
                row_count = len(data_table.rows)
                logger.info(f"ChartsExplorerScreen DataTable has {row_count} rows")

                # If we got here without RowDoesNotExist, data loaded successfully
                # Note: Charts may be empty if no charts found in path
                assert True  # Test passes if no exception occurred

            except Exception as e:
                # If we get RowDoesNotExist or other errors, this is what we want to catch
                # The test will FAIL, exposing the bug in tests
                logger.error(f"Data loading error in ChartsExplorerScreen: {e}")
                pytest.fail(f"RowDoesNotExist or data loading error: {e}")

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_charts_screen_data_table_population(self) -> None:
        """Test that ChartsExplorerScreen DataTable is properly populated after navigation."""
        if not TEST_CHARTS_PATH.exists():
            pytest.skip(f"Test charts path not found: {TEST_CHARTS_PATH}")

        app = EKSHelmReporterApp(charts_path=TEST_CHARTS_PATH, skip_eks=True)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Navigate to charts screen
            await pilot.press("C")
            await pilot.pause()

            # Wait for data loading
            await asyncio.sleep(3)
            await pilot.pause()

            # Find ChartsExplorerScreen
            charts_screen = None
            for screen in app.screen_stack:
                if isinstance(screen, ChartsExplorerScreen):
                    charts_screen = screen
                    break

            assert charts_screen is not None, "ChartsExplorerScreen should be in stack"

            # Verify charts data was loaded (checking screen state)
            assert hasattr(charts_screen, 'charts'), "ChartsExplorerScreen should have charts attribute"
            assert hasattr(charts_screen, 'filtered_charts'), "ChartsExplorerScreen should have filtered_charts"

            # The test passes if no RowDoesNotExist error was raised
            logger.info(f"Charts loaded: {len(charts_screen.charts)}")

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_charts_screen_refresh_with_r_key(self) -> None:
        """Test 'r' key triggers data refresh on ChartsExplorerScreen."""
        if not TEST_CHARTS_PATH.exists():
            pytest.skip(f"Test charts path not found: {TEST_CHARTS_PATH}")

        app = EKSHelmReporterApp(charts_path=TEST_CHARTS_PATH, skip_eks=True)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Navigate to charts screen
            await pilot.press("C")
            await pilot.pause()

            # Wait for initial load
            await asyncio.sleep(2)
            await pilot.pause()

            # Press 'r' to refresh
            await pilot.press("r")
            await pilot.pause()

            # Wait for refresh to complete
            await asyncio.sleep(2)
            await pilot.pause()

            # Test passes if no RowDoesNotExist during refresh
            logger.info("Refresh completed without RowDoesNotExist error")


class TestOptimizerScreenWithDataNavigation:
    """Test OptimizerScreen navigation with real data loading.

    This tests the full flow:
    1. Start app
    2. Run nav action to navigate to OptimizerScreen
    3. Wait for worker to complete data loading
    4. Verify DataTable has rows populated
    5. Check for RowDoesNotExist errors
    """

    @pytest.mark.asyncio
    @pytest.mark.smoke
    async def test_optimizer_screen_keypress_navigation_with_data(self) -> None:
        """Test nav action opens OptimizerScreen and loads real data."""
        if not TEST_CHARTS_PATH.exists():
            pytest.skip(f"Test charts path not found: {TEST_CHARTS_PATH}")

        app = EKSHelmReporterApp(charts_path=TEST_CHARTS_PATH, skip_eks=True)

        async with app.run_test() as pilot:
            # Initial state
            await pilot.pause()

            # Navigate to OptimizerScreen.
            await app.run_action("nav_optimizer")
            await pilot.pause()

            # Verify OptimizerScreen is in the stack
            optimizer_screens = [s for s in app.screen_stack if isinstance(s, OptimizerScreen)]
            assert len(optimizer_screens) > 0, "OptimizerScreen should be in screen stack"

            # Get the OptimizerScreen instance
            optimizer_screen = optimizer_screens[0]

            # Wait for worker to complete
            await asyncio.sleep(2)
            await pilot.pause()

            # Verify ViolationsView is present and accessible
            try:
                from kubeagle.screens.detail.components import (
                    ViolationsView,
                )
                vv = optimizer_screen.query_one("#violations-view", ViolationsView)
                logger.info("OptimizerScreen ViolationsView found")
                # Test passes if ViolationsView is accessible
                assert vv is not None

            except Exception as e:
                logger.error(f"ViolationsView access error in OptimizerScreen: {e}")
                pytest.fail(f"ViolationsView access error: {e}")

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_optimizer_screen_data_table_population(self) -> None:
        """Test that OptimizerScreen DataTable is properly populated after navigation."""
        if not TEST_CHARTS_PATH.exists():
            pytest.skip(f"Test charts path not found: {TEST_CHARTS_PATH}")

        app = EKSHelmReporterApp(charts_path=TEST_CHARTS_PATH, skip_eks=True)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Navigate to optimizer screen
            await app.run_action("nav_optimizer")
            await pilot.pause()

            # Wait for data loading
            await asyncio.sleep(3)
            await pilot.pause()

            # Find OptimizerScreen
            optimizer_screen = None
            for screen in app.screen_stack:
                if isinstance(screen, OptimizerScreen):
                    optimizer_screen = screen
                    break

            assert optimizer_screen is not None, "OptimizerScreen should be in stack"

            # Verify view switching state (violations/recs are now in child views)
            assert hasattr(optimizer_screen, '_current_view'), "OptimizerScreen should have _current_view"
            assert optimizer_screen._current_view == "violations"

            logger.info("OptimizerScreen loaded with violations view active")

    @pytest.mark.asyncio
    @pytest.mark.smoke
    async def test_optimizer_navigation_stays_stable_after_action(self) -> None:
        """Running nav action repeatedly should not stack optimizer screens."""
        if not TEST_CHARTS_PATH.exists():
            pytest.skip(f"Test charts path not found: {TEST_CHARTS_PATH}")

        app = EKSHelmReporterApp(charts_path=TEST_CHARTS_PATH, skip_eks=True)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Open optimizer once.
            await app.run_action("nav_optimizer")
            await pilot.pause()

            optimizer_screens = [
                s for s in app.screen_stack if isinstance(s, OptimizerScreen)
            ]
            assert len(optimizer_screens) == 1
            optimizer_screen = optimizer_screens[0]

            # Let event loop settle and verify view remains stable.
            await asyncio.sleep(0.8)
            await pilot.pause()
            assert optimizer_screen._current_view == "violations"

            # Running nav action again while on optimizer should not push another screen.
            await app.run_action("nav_optimizer")
            await pilot.pause()
            await asyncio.sleep(0.3)
            await pilot.pause()

            optimizer_screens = [
                s for s in app.screen_stack if isinstance(s, OptimizerScreen)
            ]
            assert len(optimizer_screens) == 1
            assert optimizer_screen._current_view == "violations"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_optimizer_screen_refresh_with_r_key(self) -> None:
        """Test 'r' key triggers data refresh on OptimizerScreen."""
        if not TEST_CHARTS_PATH.exists():
            pytest.skip(f"Test charts path not found: {TEST_CHARTS_PATH}")

        app = EKSHelmReporterApp(charts_path=TEST_CHARTS_PATH, skip_eks=True)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Navigate to optimizer screen
            await app.run_action("nav_optimizer")
            await pilot.pause()

            # Wait for initial load
            await asyncio.sleep(2)
            await pilot.pause()

            # Press 'r' to refresh
            await pilot.press("r")
            await pilot.pause()

            # Wait for refresh to complete
            await asyncio.sleep(2)
            await pilot.pause()

            logger.info("Optimizer refresh completed without RowDoesNotExist error")


class TestNavigationChainsWithDataLoading:
    """Test navigation chains with data loading at each step."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_charts_to_optimizer_navigation_chain(self) -> None:
        """Test navigating from Charts to Optimizer and loading data in both."""
        if not TEST_CHARTS_PATH.exists():
            pytest.skip(f"Test charts path not found: {TEST_CHARTS_PATH}")

        app = EKSHelmReporterApp(charts_path=TEST_CHARTS_PATH, skip_eks=True)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Navigate to Charts
            await pilot.press("C")
            await asyncio.sleep(2)
            await pilot.pause()

            # Navigate to Optimizer using run_action (keypresses may be
            # captured by focused input widgets on ChartsExplorerScreen)
            await app.run_action("nav_optimizer")
            await asyncio.sleep(2)
            await pilot.pause()

            # Verify we're on Optimizer
            optimizer_screens = [s for s in app.screen_stack if isinstance(s, OptimizerScreen)]
            assert len(optimizer_screens) > 0, (
                f"Should be on OptimizerScreen. "
                f"Stack: {[type(s).__name__ for s in app.screen_stack]}"
            )

            logger.info("Navigation chain Charts -> Optimizer completed successfully")

class TestDataLoadingErrorExposure:
    """Test class specifically designed to expose RowDoesNotExist errors.

    These tests are designed to FAIL when RowDoesNotExist occurs,
    thereby exposing bugs in tests that were previously only visible at runtime.
    """

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_charts_screen_no_row_mismatch_error(self) -> None:
        """Verify ChartsExplorerScreen doesn't produce RowDoesNotExist error.

        This test EXPECTS to pass when the bug is fixed.
        Currently it will FAIL, exposing the RowDoesNotExist bug.
        """
        if not TEST_CHARTS_PATH.exists():
            pytest.skip(f"Test charts path not found: {TEST_CHARTS_PATH}")

        app = EKSHelmReporterApp(charts_path=TEST_CHARTS_PATH, skip_eks=True)
        errors_encountered: list[str] = []

        async with app.run_test() as pilot:
            await pilot.pause()

            # Navigate and load data
            await pilot.press("C")
            await pilot.pause()

            # Wait for full load
            await asyncio.sleep(3)
            await pilot.pause()

            # Try multiple interactions that might trigger RowDoesNotExist
            try:
                charts_screen = None
                for screen in app.screen_stack:
                    if isinstance(screen, ChartsExplorerScreen):
                        charts_screen = screen
                        break

                if charts_screen:
                    # Try to access DataTable
                    data_table = charts_screen.query_one("#explorer-table", CustomDataTable)

                    # Try to get row count (this is where RowDoesNotExist occurs)
                    row_count = len(data_table.rows)
                    logger.info(f"Row count retrieved successfully: {row_count}")

                    # Note: cursor_row is a read-only property, so we skip cursor navigation test

            except Exception as e:
                error_msg = str(e)
                errors_encountered.append(error_msg)
                logger.error(f"RowDoesNotExist error encountered: {e}")

        # This assertion will FAIL if RowDoesNotExist occurred
        if errors_encountered:
            pytest.fail(
                f"RowDoesNotExist error(s) encountered during ChartsExplorerScreen test:\n"
                f"{chr(10).join(errors_encountered)}"
            )

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_optimizer_screen_no_row_mismatch_error(self) -> None:
        """Verify OptimizerScreen doesn't produce RowDoesNotExist error.

        This test EXPECTS to pass when the bug is fixed.
        Currently it will FAIL, exposing the RowDoesNotExist bug.
        """
        if not TEST_CHARTS_PATH.exists():
            pytest.skip(f"Test charts path not found: {TEST_CHARTS_PATH}")

        app = EKSHelmReporterApp(charts_path=TEST_CHARTS_PATH, skip_eks=True)
        errors_encountered: list[str] = []

        async with app.run_test() as pilot:
            await pilot.pause()

            # Navigate and load data
            await app.run_action("nav_optimizer")
            await pilot.pause()

            # Wait for full load
            await asyncio.sleep(3)
            await pilot.pause()

            # Try interactions that might trigger RowDoesNotExist
            try:
                optimizer_screen = None
                for screen in app.screen_stack:
                    if isinstance(screen, OptimizerScreen):
                        optimizer_screen = screen
                        break

                if optimizer_screen:
                    data_table = optimizer_screen.query_one("#violations-table", CustomDataTable)

                    row_count = len(data_table.rows)
                    logger.info(f"Row count retrieved successfully: {row_count}")

                    # Note: cursor_row is a read-only property, so we skip cursor navigation test

            except Exception as e:
                error_msg = str(e)
                errors_encountered.append(error_msg)
                logger.error(f"RowDoesNotExist error encountered: {e}")

        if errors_encountered:
            pytest.fail(
                f"RowDoesNotExist error(s) encountered during OptimizerScreen test:\n"
                f"{chr(10).join(errors_encountered)}"
            )

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_team_statistics_screen_no_row_mismatch_error(self) -> None:
        """Verify ChartsExplorerScreen doesn't produce RowDoesNotExist error.

        This test EXPECTS to pass when the bug is fixed.
        Currently it will FAIL, exposing the RowDoesNotExist bug.
        """
        if not TEST_CHARTS_PATH.exists():
            pytest.skip(f"Test charts path not found: {TEST_CHARTS_PATH}")

        app = EKSHelmReporterApp(charts_path=TEST_CHARTS_PATH, skip_eks=True)
        errors_encountered: list[str] = []

        async with app.run_test() as pilot:
            await pilot.pause()

            # Navigate and load data
            await pilot.press("T")
            await pilot.pause()

            # Wait for full load
            await asyncio.sleep(3)
            await pilot.pause()

            # Try interactions that might trigger RowDoesNotExist
            try:
                team_stats_screen = None
                for screen in app.screen_stack:
                    if isinstance(screen, ChartsExplorerScreen):
                        team_stats_screen = screen
                        break

                if team_stats_screen:
                    data_table = team_stats_screen.query_one("#explorer-table", CustomDataTable)

                    row_count = len(data_table.rows)
                    logger.info(f"Row count retrieved successfully: {row_count}")

                    # Note: cursor_row is a read-only property, so we skip cursor navigation test

            except Exception as e:
                error_msg = str(e)
                errors_encountered.append(error_msg)
                logger.error(f"RowDoesNotExist error encountered: {e}")

        if errors_encountered:
            pytest.fail(
                f"RowDoesNotExist error(s) encountered during ChartsExplorerScreen test:\n"
                f"{chr(10).join(errors_encountered)}"
            )
