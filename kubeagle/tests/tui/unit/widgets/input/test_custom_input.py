"""Tests for CustomInput widget."""

from __future__ import annotations

from kubeagle.widgets.input.custom_input import CustomInput


def test_custom_input_instantiation():
    """Test CustomInput instantiation."""
    input_widget = CustomInput()
    assert input_widget is not None


def test_custom_input_with_placeholder():
    """Test CustomInput with placeholder."""
    input_widget = CustomInput(placeholder="Enter text...")
    assert input_widget._placeholder == "Enter text..."


def test_custom_input_initial_value():
    """Test CustomInput initial value."""
    input_widget = CustomInput(value="Initial")
    assert input_widget._value == "Initial"


def test_custom_input_disabled():
    """Test CustomInput disabled state."""
    input_widget = CustomInput(disabled=True)
    assert input_widget._disabled is True


def test_custom_input_password():
    """Test CustomInput password mode."""
    input_widget = CustomInput(password=True)
    assert input_widget._password is True


def test_custom_input_max_length():
    """Test CustomInput max_length."""
    input_widget = CustomInput(max_length=100)
    assert input_widget._max_length == 100


def test_custom_input_changed_message():
    """Test CustomInput.Changed message class exists."""
    assert hasattr(CustomInput, 'Changed')
    assert isinstance(CustomInput.Changed, type)


def test_custom_input_submitted_message():
    """Test CustomInput.Submitted message class exists."""
    assert hasattr(CustomInput, 'Submitted')
    assert isinstance(CustomInput.Submitted, type)


def test_custom_input_css_path():
    """Test CSS path is set correctly."""
    assert CustomInput.CSS_PATH.endswith("css/widgets/custom_input.tcss")


def test_custom_input_with_id():
    """Test CustomInput with ID."""
    input_widget = CustomInput(id="input-1")
    assert input_widget.id == "input-1"


def test_custom_input_with_classes():
    """Test CustomInput with classes."""
    input_widget = CustomInput(classes="custom-class")
    assert "widget-custom-input" in input_widget.classes
    assert "custom-class" in input_widget.classes
