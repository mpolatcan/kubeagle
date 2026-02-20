"""Tests for CustomMarkdown widget."""

from __future__ import annotations

from kubeagle.widgets.display.custom_markdown import CustomMarkdown


def test_custom_markdown_instantiation():
    """Test CustomMarkdown widget instantiation."""
    markdown = CustomMarkdown(content="# Heading")
    assert markdown is not None
    assert markdown.content == "# Heading"


def test_custom_markdown_with_id():
    """Test CustomMarkdown with ID."""
    markdown = CustomMarkdown(content="Content", id="test-id")
    assert markdown.id == "test-id"


def test_custom_markdown_classes():
    """Test CSS classes are applied."""
    markdown = CustomMarkdown(content="Text", classes="custom-class")
    assert "widget-custom-markdown" in markdown.classes
    assert "custom-class" in markdown.classes


def test_custom_markdown_content_property():
    """Test content property getter."""
    markdown = CustomMarkdown(content="Test content")
    assert markdown.content == "Test content"


def test_custom_markdown_css_path():
    """Test CSS path is set correctly."""
    assert CustomMarkdown.CSS_PATH.endswith("css/widgets/custom_markdown.tcss")
