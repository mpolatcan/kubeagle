"""Tests for CustomLink widget."""

from __future__ import annotations

from kubeagle.widgets.special.custom_link import CustomLink


def test_custom_link_instantiation():
    """Test CustomLink instantiation."""
    link = CustomLink("Test Link")
    assert link is not None
    assert link.text == "Test Link"


def test_custom_link_with_url():
    """Test CustomLink with URL."""
    link = CustomLink("Click", url="https://example.com")
    assert link.url == "https://example.com"


def test_custom_link_with_tooltip():
    """Test CustomLink with tooltip."""
    link = CustomLink("Test", tooltip="This is a tooltip")
    assert link.tooltip == "This is a tooltip"


def test_custom_link_with_variant():
    """Test CustomLink with variant."""
    link = CustomLink("Test", variant="success")
    assert "success" in link.classes


def test_custom_link_default_url():
    """Test CustomLink uses text as URL when no URL provided."""
    link = CustomLink("https://example.com")
    assert link.url == "https://example.com"


def test_custom_link_disabled():
    """Test CustomLink disabled state."""
    link = CustomLink("Test", disabled=True)
    assert link.disabled is True


def test_custom_link_link_url_property():
    """Test CustomLink link_url property."""
    link = CustomLink("Test", url="https://example.com")
    assert link.link_url == "https://example.com"


def test_custom_link_link_text_property():
    """Test CustomLink link_text property."""
    link = CustomLink("Display Text")
    assert link.link_text == "Display Text"


def test_custom_link_css_path():
    """Test CSS path is set correctly."""
    assert CustomLink.CSS_PATH.endswith("css/widgets/custom_link.tcss")


def test_custom_link_with_id():
    """Test CustomLink with ID."""
    link = CustomLink("Test", id="link-1")
    assert link.id == "link-1"


def test_custom_link_with_classes():
    """Test CustomLink with classes."""
    link = CustomLink("Test", classes="custom-class")
    assert "widget-custom-link" in link.classes
    assert "custom-class" in link.classes
