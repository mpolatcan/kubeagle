"""Tests for CustomSearchBar widget."""

from __future__ import annotations

from kubeagle.widgets.filter.custom_search_bar import (
    CustomFilterButton,
    CustomSearchBar,
)


def test_custom_search_bar_instantiation():
    """Test CustomSearchBar instantiation."""
    search_bar = CustomSearchBar()
    assert search_bar is not None
    assert search_bar._placeholder == "Search..."


def test_custom_search_bar_with_placeholder():
    """Test CustomSearchBar with custom placeholder."""
    search_bar = CustomSearchBar(placeholder="Find charts...")
    assert search_bar._placeholder == "Find charts..."


def test_custom_search_bar_with_callback():
    """Test CustomSearchBar with change callback."""
    def on_change(value):
        pass

    search_bar = CustomSearchBar(on_change=on_change)
    assert search_bar._on_change is on_change


def test_custom_search_bar_css_path():
    """Test CSS path is set correctly."""
    assert CustomSearchBar.CSS_PATH.endswith("css/widgets/custom_search_bar.tcss")


def test_custom_search_bar_with_id():
    """Test CustomSearchBar with ID."""
    search_bar = CustomSearchBar(id="search-1")
    assert search_bar.id == "search-1"


def test_custom_search_bar_with_classes():
    """Test CustomSearchBar with classes."""
    search_bar = CustomSearchBar(classes="custom-class")
    assert "custom-class" in search_bar.classes


def test_custom_filter_button_instantiation():
    """Test CustomFilterButton instantiation."""
    button = CustomFilterButton(label="Filter")
    assert button is not None
    assert button._label == "Filter"


def test_custom_filter_button_with_callback():
    """Test CustomFilterButton with click callback."""
    def on_click():
        pass

    button = CustomFilterButton(label="Test", on_click=on_click)
    assert button._on_click_callback is on_click


def test_custom_filter_button_css_path():
    """Test CSS path is set correctly."""
    assert CustomFilterButton.CSS_PATH.endswith("css/widgets/custom_search_bar.tcss")


def test_custom_filter_button_with_id():
    """Test CustomFilterButton with ID."""
    button = CustomFilterButton(label="Test", id="btn-1")
    assert button.id == "btn-1"


def test_custom_filter_button_with_classes():
    """Test CustomFilterButton with classes."""
    button = CustomFilterButton(label="Test", classes="custom-class")
    assert "custom-class" in button.classes
