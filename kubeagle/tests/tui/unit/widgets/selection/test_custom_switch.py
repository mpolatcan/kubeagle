"""Tests for CustomSwitch widget."""

from __future__ import annotations

from kubeagle.widgets.selection.custom_switch import CustomSwitch


def test_custom_switch_instantiation():
    """Test CustomSwitch instantiation."""
    switch = CustomSwitch(label="Test")
    assert switch is not None
    assert switch._label == "Test"


def test_custom_switch_initial_value():
    """Test CustomSwitch initial value."""
    switch_true = CustomSwitch(value=True)
    assert switch_true._value is True

    switch_false = CustomSwitch(value=False)
    assert switch_false._value is False


def test_custom_switch_with_label():
    """Test CustomSwitch with label."""
    switch = CustomSwitch(label="My Switch")
    assert switch._label == "My Switch"


def test_custom_switch_disabled():
    """Test CustomSwitch disabled state."""
    switch_disabled = CustomSwitch(disabled=True)
    assert switch_disabled._disabled is True


def test_custom_switch_css_path():
    """Test CSS path is set correctly."""
    assert CustomSwitch.CSS_PATH.endswith("css/widgets/custom_switch.tcss")


def test_custom_switch_with_id():
    """Test CustomSwitch with ID."""
    switch = CustomSwitch(label="Test", id="switch-1")
    assert switch.id == "switch-1"


def test_custom_switch_with_classes():
    """Test CustomSwitch with classes."""
    switch = CustomSwitch(label="Test", classes="custom-class")
    assert "custom-class" in switch.classes
