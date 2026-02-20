"""Tests for CustomOptionList widget."""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult

from kubeagle.widgets.selection.custom_option_list import CustomOptionList


def test_custom_option_list_instantiation():
    """Test CustomOptionList instantiation."""
    option_list = CustomOptionList()
    assert option_list is not None


def test_custom_option_list_with_options():
    """Test CustomOptionList with options list."""
    option_list = CustomOptionList(options=["opt1", "opt2"])
    assert option_list._options == ["opt1", "opt2"]


def test_custom_option_list_disabled():
    """Test CustomOptionList disabled state."""
    option_list = CustomOptionList(disabled=True)
    assert option_list._disabled is True


def test_custom_option_list_css_path():
    """Test CSS path is set correctly."""
    assert CustomOptionList.CSS_PATH.endswith("css/widgets/custom_option_list.tcss")


def test_custom_option_list_with_id():
    """Test CustomOptionList with ID."""
    option_list = CustomOptionList(options=[], id="option-list-1")
    assert option_list.id == "option-list-1"


def test_custom_option_list_with_classes():
    """Test CustomOptionList with classes."""
    option_list = CustomOptionList(options=[], classes="custom-class")
    assert "custom-class" in option_list.classes


def _strip_text(strip) -> str:
    return "".join(segment.text for segment in strip)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_custom_option_list_horizontal_scroll_changes_visible_text() -> None:
    """Scrolling horizontally should reveal text outside the initial viewport."""

    class _ProbeApp(App[None]):
        CSS = """
        Screen {
            align: center middle;
        }
        #option-list {
            width: 26;
            height: 4;
        }
        """

        def compose(self) -> ComposeResult:
            yield CustomOptionList(
                options=["SCROLL-START-0123456789-ABCDEFGHIJ-SCROLL-END"],
                id="option-list",
            )

    app = _ProbeApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        option_list = app.query_one("#option-list", CustomOptionList).option_list
        option_list._update_lines()
        assert option_list.max_scroll_x > 0

        before = _strip_text(option_list.render_line(0))
        option_list.scroll_to(
            x=option_list.max_scroll_x,
            y=None,
            animate=False,
            force=True,
        )
        await pilot.pause()
        after = _strip_text(option_list.render_line(0))

        assert "SCROLL-START" in before
        assert "SCROLL-START" not in after
        assert before != after
