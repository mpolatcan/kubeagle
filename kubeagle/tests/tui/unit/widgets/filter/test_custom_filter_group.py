"""Tests for CustomFilterGroup widget."""

from __future__ import annotations

from kubeagle.widgets.filter.custom_filter_group import CustomFilterGroup


def test_custom_filter_group_instantiation():
    """Test CustomFilterGroup instantiation."""
    group = CustomFilterGroup(
        label="Test Group",
        options=["opt1", "opt2"],
    )
    assert group is not None
    assert group._label == "Test Group"
    assert group._options == ["opt1", "opt2"]


def test_custom_filter_group_multi_select():
    """Test CustomFilterGroup multi_select parameter."""
    group_multi = CustomFilterGroup(
        label="Multi",
        options=["a", "b"],
        multi_select=True,
    )
    assert group_multi._multi_select is True


def test_custom_filter_group_reactive_attributes():
    """Test CustomFilterGroup reactive attributes."""
    group = CustomFilterGroup(label="Test", options=["a", "b"])
    assert group.is_loading is False
    assert group.data == []
    assert group.error is None


def test_custom_filter_group_multi_select_property():
    """Test CustomFilterGroup multi_select property."""
    group = CustomFilterGroup(label="Test", options=[], multi_select=True)
    assert group.multi_select is True


def test_custom_filter_group_label_property():
    """Test CustomFilterGroup label property."""
    group = CustomFilterGroup(label="My Label", options=[])
    assert group.label == "My Label"


def test_custom_filter_group_with_callback():
    """Test CustomFilterGroup with change callback."""
    def on_change(option, active):
        pass

    group = CustomFilterGroup(
        label="Test",
        options=["a", "b"],
        on_change=on_change,
    )
    assert group._on_change is on_change


def test_custom_filter_group_css_path():
    """Test CSS path is set correctly."""
    assert CustomFilterGroup.CSS_PATH.endswith("css/widgets/custom_filter_group.tcss")


def test_custom_filter_group_with_id():
    """Test CustomFilterGroup with ID."""
    group = CustomFilterGroup(label="Test", options=[], id="filter-group-1")
    assert group.id == "filter-group-1"


def test_custom_filter_group_with_classes():
    """Test CustomFilterGroup with classes."""
    group = CustomFilterGroup(label="Test", options=[], classes="custom-class")
    assert "custom-class" in group.classes
