"""Tests for CustomKPI widget."""

from __future__ import annotations

from kubeagle.widgets.data.kpi.custom_kpi import CustomKPI


def test_custom_kpi_instantiation():
    """Test CustomKPI instantiation."""
    kpi = CustomKPI(title="Test KPI", value="100")
    assert kpi is not None
    assert kpi._title == "Test KPI"
    assert kpi._value == "100"
    assert kpi._status == "success"


def test_custom_kpi_with_status():
    """Test CustomKPI with different statuses."""
    kpi_success = CustomKPI(title="A", value="1", status="success")
    assert kpi_success._status == "success"

    kpi_warning = CustomKPI(title="B", value="2", status="warning")
    assert kpi_warning._status == "warning"

    kpi_error = CustomKPI(title="C", value="3", status="error")
    assert kpi_error._status == "error"

    kpi_info = CustomKPI(title="D", value="4", status="info")
    assert kpi_info._status == "info"


def test_custom_kpi_reactive_attributes():
    """Test CustomKPI reactive attributes."""
    kpi = CustomKPI(title="Test", value="100")
    assert kpi.is_loading is False
    assert kpi.data == []
    assert kpi.error is None


def test_custom_kpi_title_property():
    """Test CustomKPI title property."""
    kpi = CustomKPI(title="My KPI", value="100")
    assert kpi.title == "My KPI"


def test_custom_kpi_status_property():
    """Test CustomKPI status property."""
    kpi = CustomKPI(title="Test", value="100", status="warning")
    assert kpi.status == "warning"


def test_custom_kpi_watch_is_loading():
    """Test CustomKPI watch_is_loading method exists."""
    kpi = CustomKPI(title="Test", value="100")
    # Should not raise
    kpi.watch_is_loading(True)


def test_custom_kpi_watch_data():
    """Test CustomKPI watch_data method exists."""
    kpi = CustomKPI(title="Test", value="100")
    # Should not raise
    kpi.watch_data([])


def test_custom_kpi_watch_error():
    """Test CustomKPI watch_error method exists."""
    kpi = CustomKPI(title="Test", value="100")
    # Should not raise
    kpi.watch_error(None)


def test_custom_kpi_css_path():
    """Test CSS path is None (widget uses DEFAULT_CSS inline)."""
    assert CustomKPI.CSS_PATH is None


def test_custom_kpi_id_pattern():
    """Test CustomKPI has ID pattern."""
    assert CustomKPI._id_pattern == "custom-kpi-{uuid}"


def test_custom_kpi_default_classes():
    """Test CustomKPI has default classes."""
    assert CustomKPI._default_classes == "widget-custom-kpi"
