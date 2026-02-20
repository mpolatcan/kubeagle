"""Tests for CustomTabbedContent widget.

This module tests:
- CustomTabbedContent instantiation and configuration
- Composition with CustomTabPane (T6, T7 from handoff)
- Regression: TYPE_CHECKING import removed (PRD-charts-screen-fix cleanup)
"""

from __future__ import annotations

from textual.widgets import TabbedContent as TextualTabbedContent

from kubeagle.widgets.tabs.custom_tab_pane import CustomTabPane
from kubeagle.widgets.tabs.custom_tabbed_content import CustomTabbedContent

# =============================================================================
# Basic Instantiation Tests
# =============================================================================


def test_custom_tabbed_content_instantiation():
    """Test CustomTabbedContent instantiation."""
    tabbed = CustomTabbedContent("A", "B", "C")
    assert tabbed is not None
    assert tabbed._titles == ("A", "B", "C")


def test_custom_tabbed_content_with_initial():
    """Test CustomTabbedContent with initial tab."""
    tabbed = CustomTabbedContent("A", "B", initial="B")
    assert tabbed._initial == "B"


def test_custom_tabbed_content_css_path():
    """Test CSS path is set correctly."""
    assert CustomTabbedContent.CSS_PATH.endswith("css/widgets/custom_tabbed_content.tcss")


def test_custom_tabbed_content_with_id():
    """Test CustomTabbedContent with ID."""
    tabbed = CustomTabbedContent("A", "B", id="tabbed-1")
    assert tabbed.id == "tabbed-1"


def test_custom_tabbed_content_with_classes():
    """Test CustomTabbedContent with classes."""
    tabbed = CustomTabbedContent("A", "B", classes="custom-class")
    assert "custom-class" in tabbed.classes


# =============================================================================
# Inheritance and Composition Tests (PRD-charts-screen-fix)
# =============================================================================


class TestCustomTabbedContentInheritance:
    """Test CustomTabbedContent properly extends TextualTabbedContent."""

    def test_is_subclass_of_textual(self) -> None:
        """Test that CustomTabbedContent extends TextualTabbedContent."""
        assert issubclass(CustomTabbedContent, TextualTabbedContent)

    def test_instance_is_textual_tabbed_content(self) -> None:
        """Test instance is recognized as TextualTabbedContent."""
        tabbed = CustomTabbedContent("A", id="test")
        assert isinstance(tabbed, TextualTabbedContent)

    def test_no_titles_creates_empty(self) -> None:
        """Test CustomTabbedContent with no titles (E4: zero children)."""
        tabbed = CustomTabbedContent(id="empty-tabs")
        assert tabbed is not None
        assert tabbed._titles == ()


class TestCustomTabbedContentComposition:
    """Test CustomTabbedContent can be composed with CustomTabPane (T6).

    These are non-mount instantiation tests that verify object construction.
    Full widget tree composition requires a running Textual app.
    """

    def test_tab_pane_instantiation_for_composition(self) -> None:
        """Test that CustomTabPane can be created for use with TabbedContent."""
        pane = CustomTabPane("Tab 1", id="tab-1")
        assert pane is not None
        assert pane._label == "Tab 1"

    def test_multiple_tab_panes_can_be_created(self) -> None:
        """Test creating multiple CustomTabPane instances."""
        panes = [
            CustomTabPane("Tab 1", id="tab-1"),
            CustomTabPane("Tab 2", id="tab-2"),
            CustomTabPane("Tab 3", id="tab-3"),
        ]
        assert len(panes) == 3
        for i, pane in enumerate(panes, 1):
            assert pane.id == f"tab-{i}"

    def test_tabbed_content_with_standard_id(self) -> None:
        """Test TabbedContent uses standard 'tabbed-content' ID."""
        tabbed = CustomTabbedContent(id="tabbed-content")
        assert tabbed.id == "tabbed-content"

    def test_widget_custom_tabbed_content_class_applied(self) -> None:
        """Test that widget-custom-tabbed-content class is auto-applied."""
        tabbed = CustomTabbedContent("A", "B")
        assert "widget-custom-tabbed-content" in tabbed.classes


class TestCustomTabbedContentImportCleanup:
    """Test that TYPE_CHECKING import was removed (PRD-charts-screen-fix)."""

    def test_no_type_checking_import(self) -> None:
        """Test that TYPE_CHECKING is not imported in custom_tabbed_content.py."""
        import ast

        from kubeagle.widgets.tabs import custom_tabbed_content
        source_file = custom_tabbed_content.__file__
        assert source_file is not None
        with open(source_file, encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "typing":
                imported_names = [alias.name for alias in node.names]
                assert "TYPE_CHECKING" not in imported_names, (
                    "TYPE_CHECKING should not be imported in custom_tabbed_content.py"
                )
