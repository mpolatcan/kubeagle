"""Tests for CustomRadioButton widget."""

from __future__ import annotations

from kubeagle.widgets.selection.custom_radio_button import (
    CustomRadioButton,
)


def test_custom_radio_button_instantiation():
    """Test CustomRadioButton instantiation."""
    radio = CustomRadioButton(label="Test")
    assert radio is not None
    assert radio._label == "Test"


def test_custom_radio_button_initial_value():
    """Test CustomRadioButton initial value."""
    radio_true = CustomRadioButton(value=True)
    assert radio_true._value is True

    radio_false = CustomRadioButton(value=False)
    assert radio_false._value is False


def test_custom_radio_button_with_label():
    """Test CustomRadioButton with label."""
    radio = CustomRadioButton(label="My Radio")
    assert radio._label == "My Radio"


def test_custom_radio_button_disabled():
    """Test CustomRadioButton disabled state."""
    radio_disabled = CustomRadioButton(disabled=True)
    assert radio_disabled._disabled is True


def test_custom_radio_button_css_path():
    """Test CSS path is set correctly."""
    assert CustomRadioButton.CSS_PATH.endswith("css/widgets/custom_radio_button.tcss")


def test_custom_radio_button_with_id():
    """Test CustomRadioButton with ID."""
    radio = CustomRadioButton(label="Test", id="radio-1")
    assert radio.id == "radio-1"


def test_custom_radio_button_with_classes():
    """Test CustomRadioButton with classes."""
    radio = CustomRadioButton(label="Test", classes="custom-class")
    assert "custom-class" in radio.classes


def test_custom_radio_button_label_property():
    """Test CustomRadioButton label property."""
    radio = CustomRadioButton(label="Test Label")
    assert radio.label == "Test Label"
