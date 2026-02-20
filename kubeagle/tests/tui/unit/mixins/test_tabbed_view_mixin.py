"""Tests for TabbedViewMixin.

This module tests:
- TabbedViewMixin initialization and attributes
- switch_tab error handling
- get_current_tab_id correctness and None case (PRD-charts-screen-fix)
- Regression: get_current_tab_id returns active string directly
"""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import MagicMock, patch

from kubeagle.screens.mixins.tabbed_view_mixin import TabbedViewMixin


class TestTabbedViewMixin:
    """Tests for TabbedViewMixin class."""

    def test_mixin_init(self) -> None:
        """Test TabbedViewMixin initialization."""
        mixin = TabbedViewMixin()
        assert hasattr(mixin, "_current_tab")
        assert mixin._current_tab == "all"

    def test_mixin_has_switch_tab_method(self) -> None:
        """Test TabbedViewMixin has switch_tab method."""
        mixin = TabbedViewMixin()
        assert hasattr(mixin, "switch_tab")
        assert callable(mixin.switch_tab)

    def test_mixin_has_action_switch_methods(self) -> None:
        """Test TabbedViewMixin has action_switch_tab_N methods."""
        mixin = TabbedViewMixin()
        assert hasattr(mixin, "action_switch_tab_1")
        assert hasattr(mixin, "action_switch_tab_2")
        assert hasattr(mixin, "action_switch_tab_3")
        assert hasattr(mixin, "action_switch_tab_4")
        assert hasattr(mixin, "action_switch_tab_5")

    def test_mixin_has_get_current_tab_id(self) -> None:
        """Test TabbedViewMixin has get_current_tab_id method."""
        mixin = TabbedViewMixin()
        assert hasattr(mixin, "get_current_tab_id")
        assert callable(mixin.get_current_tab_id)

    def test_switch_tab_handles_error(self) -> None:
        """Test switch_tab handles errors gracefully."""
        mixin = TabbedViewMixin()
        # Should not raise exception when no query_one is available
        mixin.switch_tab("tab-1")

    def test_get_current_tab_id_returns_none_without_context(self) -> None:
        """Test get_current_tab_id returns None when no tabbed content is found (T5)."""
        mixin = TabbedViewMixin()
        result = mixin.get_current_tab_id()
        assert result is None

    def test_filterable_table_mixin_alias(self) -> None:
        """Test FilterableTableMixin is an alias for TabbedViewMixin."""
        from kubeagle.screens.mixins.tabbed_view_mixin import (
            FilterableTableMixin,
        )

        assert FilterableTableMixin is TabbedViewMixin

    def test_all_exports(self) -> None:
        """Test __all__ exports correct items."""
        from kubeagle.screens.mixins import tabbed_view_mixin

        assert "TabbedViewMixin" in tabbed_view_mixin.__all__
        assert "FilterableTableMixin" in tabbed_view_mixin.__all__


class TestGetCurrentTabIdRegression:
    """Regression tests for get_current_tab_id (PRD-charts-screen-fix).

    Before the fix, get_current_tab_id() tried to access ``.id`` on the
    ``active`` reactive string (e.g. ``tabbed_content.active.id``), which
    does not exist on ``str``.  The fix returns ``tabbed_content.active``
    directly since ``TabbedContent.active`` is already a reactive ``str``
    holding the id of the currently active ``TabPane``.
    """

    def test_returns_active_string_directly(self) -> None:
        """Test get_current_tab_id returns the active string as-is (T4).

        The reactive ``active`` attribute on ``TabbedContent`` is a plain
        string (the id of the active TabPane).  The method must return it
        directly without calling ``.id`` on it.
        """
        mixin = TabbedViewMixin()

        # Create a mock that simulates a CustomTabbedContent with active="tab-2"
        mock_tabbed_content = MagicMock()
        mock_tabbed_content.active = "tab-2"

        # Patch query_one to return our mock
        cast(Any, mixin).query_one = MagicMock(return_value=mock_tabbed_content)

        result = mixin.get_current_tab_id()
        assert result == "tab-2"
        assert isinstance(result, str)

    def test_returns_none_for_empty_active(self) -> None:
        """Test get_current_tab_id returns None when active is empty string."""
        mixin = TabbedViewMixin()

        mock_tabbed_content = MagicMock()
        mock_tabbed_content.active = ""

        cast(Any, mixin).query_one = MagicMock(return_value=mock_tabbed_content)

        result = mixin.get_current_tab_id()
        assert result is None

    def test_returns_none_when_query_one_raises(self) -> None:
        """Test get_current_tab_id returns None when query_one fails (E2)."""
        mixin = TabbedViewMixin()

        # Simulate NoMatches exception from query_one
        cast(Any, mixin).query_one = MagicMock(side_effect=Exception("No matches"))

        result = mixin.get_current_tab_id()
        assert result is None

    def test_returns_tab_id_with_hyphenated_id(self) -> None:
        """Test get_current_tab_id handles typical tab IDs like 'tab-all'."""
        mixin = TabbedViewMixin()

        mock_tabbed_content = MagicMock()
        mock_tabbed_content.active = "tab-all"

        cast(Any, mixin).query_one = MagicMock(return_value=mock_tabbed_content)

        result = mixin.get_current_tab_id()
        assert result == "tab-all"

    def test_does_not_access_id_attribute_on_active(self) -> None:
        """Test that get_current_tab_id does NOT call .id on the active string.

        This is the core regression: the old code did ``active_tab.id`` which
        failed because ``active`` is a ``str``, not a widget.
        """
        mixin = TabbedViewMixin()

        # Create a mock where .active is a string (as in real TabbedContent)
        mock_tabbed_content = MagicMock()
        # Use a real string for active, not a mock
        mock_tabbed_content.active = "tab-nodes"

        cast(Any, mixin).query_one = MagicMock(return_value=mock_tabbed_content)

        result = mixin.get_current_tab_id()

        # The result should be the string itself, not some .id attribute
        assert result == "tab-nodes"


class TestSwitchTabBehavior:
    """Test switch_tab method behavior."""

    def test_switch_tab_sets_active_on_tabbed_content(self) -> None:
        """Test that switch_tab sets the active property on TabbedContent."""
        mixin = TabbedViewMixin()

        mock_tabbed_content = MagicMock()
        cast(Any, mixin).query_one = MagicMock(return_value=mock_tabbed_content)

        mixin.switch_tab("tab-3")

        assert mock_tabbed_content.active == "tab-3"
        assert mixin._current_tab == "tab-3"

    def test_switch_tab_with_invalid_id_no_crash(self) -> None:
        """Test switch_tab with invalid ID does not crash (E3)."""
        mixin = TabbedViewMixin()

        # When query_one raises, switch_tab should silently catch
        cast(Any, mixin).query_one = MagicMock(side_effect=Exception("NoMatches"))

        # Should not raise
        mixin.switch_tab("nonexistent-tab")

    def test_action_switch_tab_1_calls_switch_tab(self) -> None:
        """Test action_switch_tab_1 delegates to switch_tab."""
        mixin = TabbedViewMixin()
        with patch.object(mixin, "switch_tab") as mocked_switch_tab:
            mixin.action_switch_tab_1()
            mocked_switch_tab.assert_called_once_with("tab-1")

    def test_action_switch_tab_5_calls_switch_tab(self) -> None:
        """Test action_switch_tab_5 delegates to switch_tab."""
        mixin = TabbedViewMixin()
        with patch.object(mixin, "switch_tab") as mocked_switch_tab:
            mixin.action_switch_tab_5()
            mocked_switch_tab.assert_called_once_with("tab-5")


class TestTabbedViewMixinImports:
    """Test that TabbedViewMixin has no unused TYPE_CHECKING import."""

    def test_no_type_checking_import(self) -> None:
        """Test that TYPE_CHECKING is not imported (cleanup from fix)."""
        import ast

        from kubeagle.screens.mixins import tabbed_view_mixin
        source_file = tabbed_view_mixin.__file__
        assert source_file is not None
        with open(source_file, encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "typing":
                imported_names = [alias.name for alias in node.names]
                assert "TYPE_CHECKING" not in imported_names, (
                    "TYPE_CHECKING should not be imported in tabbed_view_mixin.py "
                    "(removed as part of PRD-charts-screen-fix cleanup)"
                )
