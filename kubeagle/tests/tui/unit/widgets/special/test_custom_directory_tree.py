"""Tests for CustomDirectoryTree widget."""

from __future__ import annotations

from pathlib import Path

from kubeagle.widgets.special.custom_directory_tree import (
    CustomDirectoryTree,
)


def test_custom_directory_tree_instantiation():
    """Test CustomDirectoryTree instantiation."""
    tree = CustomDirectoryTree()
    assert tree is not None
    assert tree._path == Path(".")


def test_custom_directory_tree_with_path():
    """Test CustomDirectoryTree with path."""
    tree_path = CustomDirectoryTree(path=Path("/tmp"))
    assert tree_path._path == Path("/tmp")

    tree_str = CustomDirectoryTree(path="/var")
    assert tree_str._path == Path("/var")


def test_custom_directory_tree_disabled():
    """Test CustomDirectoryTree disabled state."""
    tree = CustomDirectoryTree(disabled=True)
    assert tree._disabled is True


def test_custom_directory_tree_css_path():
    """Test CSS path is set correctly."""
    assert CustomDirectoryTree.CSS_PATH.endswith("css/widgets/custom_directory_tree.tcss")


def test_custom_directory_tree_with_id():
    """Test CustomDirectoryTree with ID."""
    tree = CustomDirectoryTree(id="dir-tree-1")
    assert tree.id == "dir-tree-1"


def test_custom_directory_tree_with_classes():
    """Test CustomDirectoryTree with classes."""
    tree = CustomDirectoryTree(classes="custom-class")
    assert "widget-custom-directory-tree" in tree.classes
    assert "custom-class" in tree.classes
