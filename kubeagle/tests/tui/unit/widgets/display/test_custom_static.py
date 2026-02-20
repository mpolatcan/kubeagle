"""Tests for CustomStatic widget."""

from __future__ import annotations

from kubeagle.widgets.display.custom_static import CustomStatic


def test_custom_static_instantiation():
    """Test CustomStatic widget instantiation."""
    static = CustomStatic("Test content")
    assert static is not None


def test_custom_static_alignment():
    """Test alignment class application."""
    static_center = CustomStatic("Text", align="center")
    assert "align-center" in static_center.classes

    static_right = CustomStatic("Text", align="right")
    assert "align-right" in static_right.classes


def test_custom_static_emphasis():
    """Test emphasis class application."""
    static_emphasis = CustomStatic("Text", emphasis="success")
    assert "success" in static_emphasis.classes


def test_custom_static_css_path():
    """Test CSS path is set correctly."""
    assert CustomStatic.CSS_PATH.endswith("css/widgets/custom_static.tcss")


def test_custom_static_with_id():
    """Test CustomStatic with ID."""
    static = CustomStatic("Content", id="test-id")
    assert static.id == "test-id"


def test_custom_static_with_classes():
    """Test CustomStatic with classes."""
    static = CustomStatic("Content", classes="custom-class")
    assert "custom-class" in static.classes
