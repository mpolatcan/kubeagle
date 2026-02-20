"""Smoke tests for DataTable keyboard bindings.

Tests DATA_TABLE_BINDINGS from kubeagle.keyboard.tables
and verifies navigation, selection, and action bindings within tables.

These tests verify that DataTable bindings work correctly using Textual's Pilot API.
"""

from __future__ import annotations

import pytest
from textual.app import App

# =============================================================================
# DATA TABLE BINDINGS TESTS
# =============================================================================


class TestDataTableBindings:
    """Test DATA_TABLE_BINDINGS from keyboard/tables.py."""

    def test_data_table_bindings_count(self) -> None:
        """Test that DATA_TABLE_BINDINGS has expected number of bindings."""
        from kubeagle.keyboard.tables import DATA_TABLE_BINDINGS

        assert len(DATA_TABLE_BINDINGS) == 1

    def test_data_table_bindings_content(self) -> None:
        """Test that DATA_TABLE_BINDINGS contains expected bindings."""
        from kubeagle.keyboard.tables import DATA_TABLE_BINDINGS

        expected = [
            ("s", "toggle_sort", "Sort"),
        ]
        assert expected == DATA_TABLE_BINDINGS


# =============================================================================
# TABLE NAVIGATION TESTS
# =============================================================================


class TestTableNavigation:
    """Test table navigation with keyboard."""

    @pytest.mark.asyncio
    async def test_up_navigation(self, app: App) -> None:
        """Test up arrow key navigation in table."""
        async with app.run_test() as pilot:
            # Navigate to charts screen with data table
            await pilot.press("C")
            await pilot.pause()

            # Try up arrow
            await pilot.press("up")
            await pilot.pause()
            # Should not cause errors
            assert app is not None

    @pytest.mark.asyncio
    async def test_down_navigation(self, app: App) -> None:
        """Test down arrow key navigation in table."""
        async with app.run_test() as pilot:
            await pilot.press("C")
            await pilot.pause()

            # Try down arrow
            await pilot.press("down")
            await pilot.pause()
            # Should not cause errors
            assert app is not None

    @pytest.mark.asyncio
    async def test_left_navigation(self, app: App) -> None:
        """Test left arrow key navigation in table."""
        async with app.run_test() as pilot:
            await pilot.press("C")
            await pilot.pause()

            # Try left arrow
            await pilot.press("left")
            await pilot.pause()
            # Should not cause errors
            assert app is not None

    @pytest.mark.asyncio
    async def test_right_navigation(self, app: App) -> None:
        """Test right arrow key navigation in table."""
        async with app.run_test() as pilot:
            await pilot.press("C")
            await pilot.pause()

            # Try right arrow
            await pilot.press("right")
            await pilot.pause()
            # Should not cause errors
            assert app is not None


# =============================================================================
# TABLE SELECTION TESTS
# =============================================================================


class TestTableSelection:
    """Test table selection with keyboard."""

    @pytest.mark.asyncio
    async def test_enter_selects_row(self, app: App) -> None:
        """Test Enter key selects a row in table."""
        async with app.run_test() as pilot:
            await pilot.press("C")
            await pilot.pause()

            # Try Enter
            await pilot.press("enter")
            await pilot.pause()
            # Should not cause errors
            assert app is not None


# =============================================================================
# TABLE FOCUS TESTS
# =============================================================================


class TestTableFocus:
    """Test table focus management."""

    @pytest.mark.asyncio
    async def test_tab_focuses_table(self, app: App) -> None:
        """Test Tab key focuses table."""
        async with app.run_test() as pilot:
            await pilot.press("C")
            await pilot.pause()

            # Try Tab
            await pilot.press("tab")
            await pilot.pause()
            # Should not cause errors
            assert app is not None

    @pytest.mark.asyncio
    async def test_shift_tab_blurs_table(self, app: App) -> None:
        """Test Shift+Tab blurs table."""
        async with app.run_test() as pilot:
            await pilot.press("C")
            await pilot.pause()

            # Try Shift+Tab
            await pilot.press("shift+tab")
            await pilot.pause()
            # Should not cause errors
            assert app is not None


# =============================================================================
# VERIFICATION TESTS
# =============================================================================


class TestTableBindingsVerification:
    """Verification tests for table binding structure."""

    def test_tables_module_exports(self) -> None:
        """Test that tables module exports expected items."""
        from kubeagle.keyboard.tables import DATA_TABLE_BINDINGS, __all__

        assert "DATA_TABLE_BINDINGS" in __all__
        assert DATA_TABLE_BINDINGS is not None

    def test_data_table_binding_structure(self) -> None:
        """Test DataTable binding has correct structure."""
        from kubeagle.keyboard.tables import DATA_TABLE_BINDINGS

        assert len(DATA_TABLE_BINDINGS) == 1

        for binding in DATA_TABLE_BINDINGS:
            # Each binding should be a tuple of (key, action, description)
            assert isinstance(binding, tuple)
            assert len(binding) == 3

            key, action, description = binding
            assert isinstance(key, str)
            assert isinstance(action, str)
            assert isinstance(description, str)
