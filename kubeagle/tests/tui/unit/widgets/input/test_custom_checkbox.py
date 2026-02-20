"""Tests for CustomCheckbox widget."""

from __future__ import annotations

from kubeagle.widgets.input.custom_checkbox import CustomCheckbox


def test_custom_checkbox_instantiation():
    """Test CustomCheckbox instantiation."""
    checkbox = CustomCheckbox(label="Test")
    assert checkbox is not None
    assert checkbox._label == "Test"


def test_custom_checkbox_initial_value():
    """Test CustomCheckbox initial value."""
    checkbox_true = CustomCheckbox(value=True)
    assert checkbox_true._value is True

    checkbox_false = CustomCheckbox(value=False)
    assert checkbox_false._value is False


def test_custom_checkbox_with_label():
    """Test CustomCheckbox with label."""
    checkbox = CustomCheckbox(label="My Checkbox")
    assert checkbox._label == "My Checkbox"


def test_custom_checkbox_disabled():
    """Test CustomCheckbox disabled state."""
    checkbox_disabled = CustomCheckbox(disabled=True)
    assert checkbox_disabled._disabled is True


def test_custom_checkbox_css_path():
    """Test CSS path is set correctly."""
    assert CustomCheckbox.CSS_PATH.endswith("css/widgets/custom_checkbox.tcss")


def test_custom_checkbox_with_id():
    """Test CustomCheckbox with ID."""
    checkbox = CustomCheckbox(label="Test", id="checkbox-1")
    assert checkbox.id == "checkbox-1"


def test_custom_checkbox_with_classes():
    """Test CustomCheckbox with classes."""
    checkbox = CustomCheckbox(label="Test", classes="custom-class")
    assert "widget-custom-checkbox" in checkbox.classes
    assert "custom-class" in checkbox.classes
