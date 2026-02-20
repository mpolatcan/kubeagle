"""Tests for CustomContentSwitcher widget."""

from __future__ import annotations

from kubeagle.widgets.special.custom_content_switcher import (
    CustomContentSwitcher,
)


def test_custom_content_switcher_instantiation():
    """Test CustomContentSwitcher instantiation."""
    switcher = CustomContentSwitcher()
    assert switcher is not None


def test_custom_content_switcher_with_initial():
    """Test CustomContentSwitcher with initial child."""
    switcher = CustomContentSwitcher(initial="panel-1")
    assert switcher._initial == "panel-1"


def test_custom_content_switcher_css_path():
    """Test CSS path is set correctly."""
    assert CustomContentSwitcher.CSS_PATH.endswith("css/widgets/custom_content_switcher.tcss")


def test_custom_content_switcher_with_id():
    """Test CustomContentSwitcher with ID."""
    switcher = CustomContentSwitcher(id="switcher-1")
    assert switcher.id == "switcher-1"


def test_custom_content_switcher_with_classes():
    """Test CustomContentSwitcher with classes."""
    switcher = CustomContentSwitcher(classes="custom-class")
    assert "widget-custom-content-switcher" in switcher.classes
    assert "custom-class" in switcher.classes
