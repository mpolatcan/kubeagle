"""Tests for CustomSelectionList widget."""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult
from textual.widgets._selection_list import Selection

from kubeagle.widgets.selection.custom_selection_list import (
    CustomSelectionList,
)


def test_custom_selection_list_instantiation():
    """Test CustomSelectionList instantiation."""
    selection_list = CustomSelectionList()
    assert selection_list is not None


def test_custom_selection_list_with_selections():
    """Test CustomSelectionList with Selection objects."""
    selections = [
        Selection("A", value="a"),
        Selection("B", value="b"),
    ]
    selection_list = CustomSelectionList(*selections)
    assert selection_list._selections == tuple(selections)


def test_custom_selection_list_disabled():
    """Test CustomSelectionList disabled state."""
    selection_list = CustomSelectionList(disabled=True)
    assert selection_list._disabled is True


def test_custom_selection_list_compact():
    """Test CustomSelectionList compact mode."""
    selection_list = CustomSelectionList(compact=True)
    assert selection_list._compact is True


def test_custom_selection_list_css_path():
    """Test CSS path is set correctly."""
    assert CustomSelectionList.CSS_PATH.endswith("css/widgets/custom_selection_list.tcss")


def test_custom_selection_list_with_id():
    """Test CustomSelectionList with ID."""
    selection_list = CustomSelectionList(id="selection-list-1")
    assert selection_list.id == "selection-list-1"


def test_custom_selection_list_with_classes():
    """Test CustomSelectionList with classes."""
    selection_list = CustomSelectionList(classes="custom-class")
    assert "custom-class" in selection_list.classes


def _strip_text(strip) -> str:
    return "".join(segment.text for segment in strip)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_custom_selection_list_horizontal_scroll_changes_visible_text() -> None:
    """Scrolling horizontally should reveal text outside the initial viewport."""

    class _ProbeApp(App[None]):
        CSS = """
        Screen {
            align: center middle;
        }
        #selection-list {
            width: 30;
            height: 4;
        }
        """

        def compose(self) -> ComposeResult:
            yield CustomSelectionList(
                Selection(
                    "SCROLL-START-0123456789-ABCDEFGHIJ-SCROLL-END",
                    value="long-option",
                ),
                id="selection-list",
            )

    app = _ProbeApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        selection_list = app.query_one(
            "#selection-list",
            CustomSelectionList,
        ).selection_list
        assert selection_list is not None
        selection_list._update_lines()
        assert selection_list.max_scroll_x > 0

        before = _strip_text(selection_list.render_line(0))
        selection_list.scroll_to(
            x=selection_list.max_scroll_x,
            y=None,
            animate=False,
            force=True,
        )
        await pilot.pause()
        after = _strip_text(selection_list.render_line(0))

        assert "SCROLL-START" in before
        assert "SCROLL-START" not in after
        assert before != after
