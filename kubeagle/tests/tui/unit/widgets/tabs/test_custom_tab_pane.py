"""Tests for CustomTabPane widget."""

from __future__ import annotations

from textual.widgets import Static

from kubeagle.widgets.tabs.custom_tab_pane import CustomTabPane


def test_custom_tab_pane_instantiation():
    """Test CustomTabPane instantiation."""
    pane = CustomTabPane(label="Test")
    assert pane is not None
    assert pane._label == "Test"


def test_custom_tab_pane_with_widgets():
    """Test CustomTabPane with child widgets."""
    pane = CustomTabPane(Static("Content"), label="Tab")
    assert len(pane._widgets) == 1


def test_custom_tab_pane_with_string_label():
    """Test CustomTabPane with string as first argument."""
    pane = CustomTabPane("Label Text")
    assert pane._label == "Label Text"


def test_custom_tab_pane_disabled():
    """Test CustomTabPane disabled state."""
    pane = CustomTabPane(label="Test", disabled=True)
    assert pane._disabled is True


def test_custom_tab_pane_css_path():
    """Test CSS path is set correctly."""
    assert CustomTabPane.CSS_PATH.endswith("css/widgets/custom_tab_pane.tcss")


def test_custom_tab_pane_with_id():
    """Test CustomTabPane with ID."""
    pane = CustomTabPane(label="Test", id="tab-pane-1")
    assert pane.id == "tab-pane-1"


def test_custom_tab_pane_with_classes():
    """Test CustomTabPane with classes."""
    pane = CustomTabPane(label="Test", classes="custom-class")
    assert "custom-class" in pane.classes


def test_custom_tab_pane_label_property():
    """Test CustomTabPane label property."""
    pane = CustomTabPane(label="My Label")
    assert pane.label == "My Label"
