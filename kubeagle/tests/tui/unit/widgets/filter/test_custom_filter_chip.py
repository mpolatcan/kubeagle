"""Tests for CustomFilterChip widget."""

from __future__ import annotations

from kubeagle.widgets.filter.custom_filter_chip import CustomFilterChip


def test_custom_filter_chip_instantiation():
    """Test CustomFilterChip instantiation."""
    chip = CustomFilterChip(label="Test Chip")
    assert chip is not None
    assert chip._label == "Test Chip"


def test_custom_filter_chip_reactive_attributes():
    """Test CustomFilterChip reactive attributes."""
    chip = CustomFilterChip(label="Test")
    assert chip.is_loading is False
    assert chip.data == []
    assert chip.error is None


def test_custom_filter_chip_with_callback():
    """Test CustomFilterChip with toggle callback."""
    def on_toggle(active):
        pass

    chip = CustomFilterChip(label="Test", on_toggle=on_toggle)
    assert chip._on_toggle is on_toggle


def test_custom_filter_chip_initial_active_state():
    """Test CustomFilterChip initial active state."""
    chip = CustomFilterChip(label="Test", active=True)
    assert chip.is_active is True


def test_custom_filter_chip_css_path():
    """Test CSS path is set correctly."""
    assert CustomFilterChip.CSS_PATH.endswith("css/widgets/custom_filter_chip.tcss")


def test_custom_filter_chip_with_id():
    """Test CustomFilterChip with ID."""
    chip = CustomFilterChip(label="Test", id="chip-1")
    assert chip.id == "chip-1"


def test_custom_filter_chip_with_classes():
    """Test CustomFilterChip with classes."""
    chip = CustomFilterChip(label="Test", classes="custom-class")
    assert "custom-class" in chip.classes


def test_custom_filter_chip_label_property():
    """Test CustomFilterChip label property."""
    chip = CustomFilterChip(label="My Label")
    assert chip.label == "My Label"
