"""Tests for CustomTextArea widget."""

from __future__ import annotations

from kubeagle.widgets.input.custom_text_area import CustomTextArea


def test_custom_text_area_instantiation():
    """Test CustomTextArea instantiation."""
    text_area = CustomTextArea()
    assert text_area is not None


def test_custom_text_area_with_text():
    """Test CustomTextArea with initial text."""
    text_area = CustomTextArea(text="Initial content")
    assert text_area._text == "Initial content"


def test_custom_text_area_with_placeholder():
    """Test CustomTextArea with placeholder."""
    text_area = CustomTextArea(placeholder="Enter...")
    assert text_area._placeholder == "Enter..."


def test_custom_text_area_disabled():
    """Test CustomTextArea disabled state."""
    text_area = CustomTextArea(disabled=True)
    assert text_area._disabled is True


def test_custom_text_area_language():
    """Test CustomTextArea language for syntax highlighting."""
    text_area = CustomTextArea(language="python")
    assert text_area._language == "python"


def test_custom_text_area_show_line_numbers():
    """Test CustomTextArea show_line_numbers."""
    text_area = CustomTextArea(show_line_numbers=True)
    assert text_area._show_line_numbers is True


def test_custom_text_area_read_only():
    """Test CustomTextArea read_only."""
    text_area = CustomTextArea(read_only=True)
    assert text_area._read_only is True


def test_custom_text_area_css_path():
    """Test CSS path is set correctly."""
    assert CustomTextArea.CSS_PATH.endswith("css/widgets/custom_text_area.tcss")


def test_custom_text_area_with_id():
    """Test CustomTextArea with ID."""
    text_area = CustomTextArea(id="text-area-1")
    assert text_area.id == "text-area-1"


def test_custom_text_area_with_classes():
    """Test CustomTextArea with classes."""
    text_area = CustomTextArea(classes="custom-class")
    assert "custom-class" in text_area.classes
