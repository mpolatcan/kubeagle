"""Tests for CustomHeader widget."""

from __future__ import annotations

from kubeagle.widgets.structure.custom_header import CustomHeader


def test_custom_header_instantiation():
    """Test CustomHeader instantiation."""
    header = CustomHeader()
    assert header is not None


def test_custom_header_css_path():
    """Test CSS path is set correctly."""
    assert CustomHeader.CSS_PATH.endswith("css/widgets/custom_header.tcss")


def test_custom_header_with_id():
    """Test CustomHeader with ID."""
    header = CustomHeader(id="header-1")
    assert header.id == "header-1"


def test_custom_header_with_classes():
    """Test CustomHeader with classes."""
    header = CustomHeader(classes="custom-class")
    assert "custom-class" in header.classes
