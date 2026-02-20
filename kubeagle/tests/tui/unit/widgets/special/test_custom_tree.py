"""Tests for CustomTree widget."""

from __future__ import annotations

from kubeagle.widgets.special.custom_tree import CustomTree


def test_custom_tree_instantiation():
    """Test CustomTree instantiation."""
    tree = CustomTree()
    assert tree is not None
    assert tree._label == ""


def test_custom_tree_with_label():
    """Test CustomTree with label."""
    tree = CustomTree(label="File System")
    assert tree._label == "File System"


def test_custom_tree_disabled():
    """Test CustomTree disabled state."""
    tree = CustomTree(disabled=True)
    assert tree._disabled is True


def test_custom_tree_node_selected_message():
    """Test CustomTree.NodeSelected message class exists."""
    assert hasattr(CustomTree, 'NodeSelected')
    assert isinstance(CustomTree.NodeSelected, type)


def test_custom_tree_css_path():
    """Test CSS path is set correctly."""
    assert CustomTree.CSS_PATH.endswith("css/widgets/custom_tree.tcss")


def test_custom_tree_with_id():
    """Test CustomTree with ID."""
    tree = CustomTree(id="tree-1")
    assert tree.id == "tree-1"


def test_custom_tree_with_classes():
    """Test CustomTree with classes."""
    tree = CustomTree(classes="custom-class")
    assert "custom-class" in tree.classes
