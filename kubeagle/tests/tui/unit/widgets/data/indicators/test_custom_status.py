"""Tests for CustomStatusIndicator widgets."""

from __future__ import annotations

from textual.app import App

from kubeagle.widgets.data.indicators.custom_status import (
    CustomErrorRetryWidget,
    CustomLastUpdatedWidget,
    CustomStatusIndicator,
)


class StatusWidgetsApp(App):
    """Test app for status widgets."""

    def compose(self):
        yield CustomStatusIndicator(status="success", label="Healthy")
        yield CustomErrorRetryWidget(error_message="Failed to load")
        yield CustomLastUpdatedWidget(timestamp="2024-01-15 10:30")


def test_custom_status_indicator_instantiation():
    """Test CustomStatusIndicator instantiation."""
    indicator = CustomStatusIndicator(status="success")
    assert indicator is not None
    assert indicator._status == "success"


def test_custom_status_indicator_with_label():
    """Test CustomStatusIndicator with label."""
    indicator = CustomStatusIndicator(status="warning", label="Warning!")
    assert indicator._label == "Warning!"


def test_custom_status_indicator_with_classes():
    """Test CustomStatusIndicator with classes."""
    indicator = CustomStatusIndicator(classes="custom-class")
    assert "widget-custom-status-indicator" in indicator.classes
    assert "custom-class" in indicator.classes


def test_custom_status_indicator_set_status():
    """Test CustomStatusIndicator set_status method."""
    indicator = CustomStatusIndicator(status="success")
    indicator.set_status("error")
    assert indicator._status == "error"


def test_custom_status_indicator_status_property():
    """Test CustomStatusIndicator status property."""
    indicator = CustomStatusIndicator(status="info")
    assert indicator.status == "info"


def test_custom_status_indicator_css_path():
    """Test CSS path is set correctly."""
    assert CustomStatusIndicator.CSS_PATH.endswith("css/widgets/custom_status.tcss")


def test_custom_error_retry_widget_instantiation():
    """Test CustomErrorRetryWidget instantiation."""
    widget = CustomErrorRetryWidget(error_message="Test error")
    assert widget is not None
    assert widget._error_message == "Test error"


def test_custom_error_retry_widget_with_id():
    """Test CustomErrorRetryWidget with ID."""
    widget = CustomErrorRetryWidget(error_message="Test", id="error-widget")
    assert widget.id == "error-widget"


def test_custom_error_retry_widget_with_classes():
    """Test CustomErrorRetryWidget with classes."""
    widget = CustomErrorRetryWidget(error_message="Test", classes="custom-class")
    assert "widget-custom-error-retry" in widget.classes
    assert "custom-class" in widget.classes


def test_custom_error_retry_widget_set_error():
    """Test CustomErrorRetryWidget set_error method."""
    widget = CustomErrorRetryWidget(error_message="Original")
    widget.set_error("Updated error")
    assert widget._error_message == "Updated error"


def test_custom_error_retry_widget_action_retry():
    """Test CustomErrorRetryWidget action_retry method."""
    widget = CustomErrorRetryWidget(error_message="Test")
    # Should not raise
    widget.action_retry()


def test_custom_error_retry_widget_bindings():
    """Test CustomErrorRetryWidget bindings exist."""
    bindings = CustomErrorRetryWidget.BINDINGS
    assert ("enter", "retry", "Retry") in bindings
    assert ("r", "retry", "Retry") in bindings


def test_custom_error_retry_widget_css_path():
    """Test CSS path is set correctly."""
    assert CustomErrorRetryWidget.CSS_PATH.endswith("css/widgets/custom_status.tcss")


def test_custom_last_updated_widget_instantiation():
    """Test CustomLastUpdatedWidget instantiation."""
    widget = CustomLastUpdatedWidget(timestamp="2024-01-15")
    assert widget is not None
    assert widget._timestamp == "2024-01-15"


def test_custom_last_updated_widget_default():
    """Test CustomLastUpdatedWidget default timestamp."""
    widget = CustomLastUpdatedWidget()
    assert widget._timestamp == "Not yet loaded"


def test_custom_last_updated_widget_with_classes():
    """Test CustomLastUpdatedWidget with classes."""
    widget = CustomLastUpdatedWidget(classes="custom-class")
    assert "widget-custom-last-updated" in widget.classes
    assert "custom-class" in widget.classes


def test_custom_last_updated_widget_update():
    """Test CustomLastUpdatedWidget update method."""
    widget = CustomLastUpdatedWidget()
    widget.update("2024-02-01 12:00")
    assert widget._timestamp == "2024-02-01 12:00"


def test_custom_last_updated_widget_get_display_text():
    """Test CustomLastUpdatedWidget get_display_text method."""
    widget_with_time = CustomLastUpdatedWidget(timestamp="2024-01-15")
    assert "Last updated: 2024-01-15" in widget_with_time._get_display_text()

    widget_no_time = CustomLastUpdatedWidget()
    assert "Not yet loaded" in widget_no_time._get_display_text()


def test_custom_last_updated_widget_css_path():
    """Test CSS path is set correctly."""
    assert CustomLastUpdatedWidget.CSS_PATH.endswith("css/widgets/custom_status.tcss")
