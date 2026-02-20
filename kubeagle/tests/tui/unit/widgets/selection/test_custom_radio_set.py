"""Tests for CustomRadioSet widget."""

from __future__ import annotations

from kubeagle.widgets.selection.custom_radio_set import CustomRadioSet


def test_custom_radio_set_instantiation():
    """Test CustomRadioSet instantiation."""
    radio_set = CustomRadioSet("A", "B", "C")
    assert radio_set is not None
    assert radio_set._labels == ("A", "B", "C")


def test_custom_radio_set_compact():
    """Test CustomRadioSet compact mode."""
    radio_compact = CustomRadioSet("X", "Y", compact=True)
    assert radio_compact._compact is True


def test_custom_radio_set_disabled():
    """Test CustomRadioSet disabled state."""
    radio_disabled = CustomRadioSet("A", "B", disabled=True)
    assert radio_disabled._disabled is True


def test_custom_radio_set_css_path():
    """Test CSS path is set correctly."""
    assert CustomRadioSet.CSS_PATH.endswith("css/widgets/custom_radio_set.tcss")


def test_custom_radio_set_with_id():
    """Test CustomRadioSet with ID."""
    radio_set = CustomRadioSet("A", "B", id="radio-set-1")
    assert radio_set.id == "radio-set-1"


def test_custom_radio_set_with_classes():
    """Test CustomRadioSet with classes."""
    radio_set = CustomRadioSet("A", "B", classes="custom-class")
    assert "custom-class" in radio_set.classes
