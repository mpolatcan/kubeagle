"""Tests for CustomRichLog widget."""

from __future__ import annotations

from textual.app import App

from kubeagle.widgets.display.custom_rich_log import CustomRichLog


class CustomRichLogApp(App):
    """Test app for CustomRichLog widget."""

    def compose(self):
        yield CustomRichLog(id="log-viewer", highlight=True, wrap=False)
        yield CustomRichLog(id="log-with-max-lines", max_lines=100)


def test_custom_rich_log_instantiation():
    """Test CustomRichLog widget instantiation."""
    rich_log = CustomRichLog()
    assert rich_log is not None


def test_custom_rich_log_with_id():
    """Test CustomRichLog with ID."""
    rich_log = CustomRichLog(id="test-log")
    assert rich_log.id == "test-log"


def test_custom_rich_log_classes():
    """Test CSS classes are applied."""
    rich_log = CustomRichLog(classes="custom-class")
    assert "widget-custom-rich-log" in rich_log.classes
    assert "custom-class" in rich_log.classes


def test_custom_rich_log_disabled():
    """Test disabled state."""
    rich_log_disabled = CustomRichLog(disabled=True)
    assert rich_log_disabled.disabled is True


def test_custom_rich_log_highlight():
    """Test highlight parameter."""
    rich_log_highlight = CustomRichLog(highlight=True)
    assert rich_log_highlight._highlight is True


def test_custom_rich_log_wrap():
    """Test wrap parameter."""
    rich_log_wrap = CustomRichLog(wrap=True)
    assert rich_log_wrap._wrap is True

    rich_log_no_wrap = CustomRichLog(wrap=False)
    assert rich_log_no_wrap._wrap is False


def test_custom_rich_log_max_lines():
    """Test max_lines parameter."""
    rich_log_max = CustomRichLog(max_lines=500)
    assert rich_log_max._max_lines == 500


def test_custom_rich_log_rich_log_property():
    """Test rich_log property returns underlying widget."""
    rich_log = CustomRichLog()
    # Before mounting, should be None
    assert rich_log.rich_log is None


def test_custom_rich_log_clear():
    """Test clear method."""
    rich_log = CustomRichLog()
    # Should not raise
    rich_log.clear()


def test_custom_rich_log_write():
    """Test write method."""
    rich_log = CustomRichLog()
    # Should not raise
    rich_log.write("Test line")


def test_custom_rich_log_css_path():
    """Test CSS path is set correctly."""
    assert CustomRichLog.CSS_PATH.endswith("css/widgets/custom_rich_log.tcss")
