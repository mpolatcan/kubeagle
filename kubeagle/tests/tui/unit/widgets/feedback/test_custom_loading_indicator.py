"""Tests for CustomLoadingIndicator widget."""

from __future__ import annotations

from textual.app import App

from kubeagle.widgets.feedback.custom_loading_indicator import (
    CustomLoadingIndicator,
)


class CustomLoadingIndicatorApp(App):
    """Test app for CustomLoadingIndicator widget."""

    def compose(self):
        yield CustomLoadingIndicator()
        yield CustomLoadingIndicator(id="loading-test")


def test_custom_loading_indicator_instantiation():
    """Test CustomLoadingIndicator widget instantiation."""
    indicator = CustomLoadingIndicator()
    assert indicator is not None


def test_custom_loading_indicator_with_id():
    """Test CustomLoadingIndicator with ID."""
    indicator = CustomLoadingIndicator(id="test-indicator")
    assert indicator._id == "test-indicator"


def test_custom_loading_indicator_classes():
    """Test CSS classes are applied."""
    indicator = CustomLoadingIndicator(classes="custom-class")
    assert "widget-custom-loading-indicator" in indicator.classes
    assert "custom-class" in indicator.classes


def test_custom_loading_indicator_disabled():
    """Test disabled state."""
    indicator_disabled = CustomLoadingIndicator(disabled=True)
    assert indicator_disabled._disabled is True


def test_custom_loading_indicator_loading_indicator_property():
    """Test loading_indicator property returns underlying widget."""
    indicator = CustomLoadingIndicator()
    # Before mounting, should be None
    assert indicator.loading_indicator is None


def test_custom_loading_indicator_css_path():
    """Test CSS path is set correctly."""
    assert CustomLoadingIndicator.CSS_PATH.endswith("css/widgets/custom_loading_indicator.tcss")
