"""Tests for CustomButton widget."""

from __future__ import annotations

from textual.app import App

from kubeagle.widgets.feedback.custom_button import CustomButton


class CustomButtonApp(App):
    """Test app for CustomButton widget."""

    def compose(self):
        yield CustomButton("Click me", variant="primary")
        yield CustomButton("Secondary", variant="default")
        yield CustomButton("Destructive", variant="error", compact=True)


def test_custom_button_instantiation():
    """Test CustomButton widget instantiation."""
    button = CustomButton("Test Button")
    assert button is not None
    assert button.label == "Test Button"


def test_custom_button_variants():
    """Test button variant class application."""
    button_default = CustomButton("Default")
    assert button_default._variant == "default"

    button_primary = CustomButton("Primary", variant="primary")
    assert button_primary._variant == "primary"

    button_success = CustomButton("Success", variant="success")
    assert button_success._variant == "success"

    button_warning = CustomButton("Warning", variant="warning")
    assert button_warning._variant == "warning"

    button_error = CustomButton("Error", variant="error")
    assert button_error._variant == "error"


def test_custom_button_compact():
    """Test compact mode."""
    button_compact = CustomButton("Compact", compact=True)
    assert button_compact._compact is True

    button_regular = CustomButton("Regular", compact=False)
    assert button_regular._compact is False


def test_custom_button_disabled():
    """Test disabled state."""
    button_disabled = CustomButton("Disabled", disabled=True)
    assert button_disabled.disabled is True


def test_custom_button_clicked_message():
    """Test CustomButton.Clicked message class exists."""
    _button = CustomButton("Test")
    assert hasattr(CustomButton, 'Clicked')
    # The message should be a class
    assert isinstance(CustomButton.Clicked, type)


def test_custom_button_default_css():
    """Test DEFAULT_CSS is set with hover styles."""
    assert "background: $primary" in CustomButton.DEFAULT_CSS
    assert "$surface-darken-3" in CustomButton.DEFAULT_CSS


def test_custom_button_with_id():
    """Test CustomButton with ID."""
    button = CustomButton("Content", id="test-btn")
    assert button.id == "test-btn"


def test_custom_button_classes():
    """Test CSS classes are applied."""
    button = CustomButton("Test", classes="custom-class")
    assert "custom-class" in button.classes
