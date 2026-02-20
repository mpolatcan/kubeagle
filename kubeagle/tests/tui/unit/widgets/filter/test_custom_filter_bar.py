"""Tests for CustomFilterBar widget."""

from __future__ import annotations

from kubeagle.widgets.filter.custom_filter_bar import (
    CustomFilterBar,
    CustomFilterStats,
)


def test_custom_filter_stats_instantiation():
    """Test CustomFilterStats instantiation."""
    stats = CustomFilterStats(total=10)
    assert stats is not None
    assert stats._total == 10


def test_custom_filter_stats_with_filtered():
    """Test CustomFilterStats with filtered value."""
    stats = CustomFilterStats(total=100, filtered=75)
    assert stats._filtered == 75


def test_custom_filter_stats_reactive_attributes():
    """Test CustomFilterStats reactive attributes."""
    stats = CustomFilterStats(total=10)
    assert stats.is_loading is False
    assert stats.data == []
    assert stats.error is None


def test_custom_filter_stats_css_path():
    """Test CSS path is set correctly."""
    assert CustomFilterStats.CSS_PATH.endswith("css/widgets/custom_filter_bar.tcss")


def test_custom_filter_bar_instantiation():
    """Test CustomFilterBar instantiation."""
    bar = CustomFilterBar()
    assert bar is not None
    assert bar._placeholder == "Search..."


def test_custom_filter_bar_with_options():
    """Test CustomFilterBar with filter options."""
    bar = CustomFilterBar(
        filter_options=["opt1", "opt2", "opt3"],
    )
    assert bar._filter_options == ["opt1", "opt2", "opt3"]


def test_custom_filter_bar_with_callback():
    """Test CustomFilterBar with callback."""
    def on_filter(_search, _filters):
        pass

    bar = CustomFilterBar(on_filter=on_filter)
    assert bar._on_filter is on_filter


def test_custom_filter_bar_show_stats():
    """Test CustomFilterBar show_stats parameter."""
    bar_with_stats = CustomFilterBar(show_stats=True)
    assert bar_with_stats._show_stats is True

    bar_without_stats = CustomFilterBar(show_stats=False)
    assert bar_without_stats._show_stats is False


def test_custom_filter_bar_reactive_attributes():
    """Test CustomFilterBar reactive attributes."""
    bar = CustomFilterBar()
    assert bar.is_loading is False
    assert bar.data == []
    assert bar.error is None


def test_custom_filter_bar_css_path():
    """Test CSS path is set correctly."""
    assert CustomFilterBar.CSS_PATH.endswith("css/widgets/custom_filter_bar.tcss")


def test_custom_filter_bar_with_id():
    """Test CustomFilterBar with ID."""
    bar = CustomFilterBar(id="filter-bar-1")
    assert bar.id == "filter-bar-1"


def test_custom_filter_bar_with_classes():
    """Test CustomFilterBar with classes."""
    bar = CustomFilterBar(classes="custom-class")
    assert "custom-class" in bar.classes
