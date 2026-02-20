"""Tests for CustomTabs and CustomTab widgets.

This module tests:
- CustomTabs instantiation and configuration
- CustomTab instantiation, label_text property, and native label passthrough
- Regression: CustomTab.label does NOT shadow TextualTab.label (PRD-charts-screen-fix)
"""

from __future__ import annotations

from textual.content import Content
from textual.widgets import Tab as TextualTab

from kubeagle.widgets.tabs.custom_tabs import CustomTab, CustomTabs

# =============================================================================
# CustomTabs Tests
# =============================================================================


def test_custom_tabs_instantiation():
    """Test CustomTabs instantiation."""
    tabs = CustomTabs()
    assert tabs is not None


def test_custom_tabs_with_tabs():
    """Test CustomTabs with tabs configuration."""
    tabs_config: list[dict[str, str]] = [
        {"id": "tab1", "label": "Tab 1"},
        {"id": "tab2", "label": "Tab 2", "disabled": "true"},
    ]
    tabs = CustomTabs(tabs=tabs_config)
    assert len(tabs._tabs_config) == 2


def test_custom_tabs_with_active():
    """Test CustomTabs with initial active tab."""
    tabs = CustomTabs(active="tab1")
    assert tabs._active == "tab1"


def test_custom_tabs_with_callback():
    """Test CustomTabs with on_change callback."""
    def on_change(tab_id):
        pass

    tabs = CustomTabs(on_change=on_change)
    assert tabs._on_change is on_change


def test_custom_tabs_css_path():
    """Test CSS path is set correctly."""
    assert CustomTabs.CSS_PATH.endswith("css/widgets/custom_tabs.tcss")


def test_custom_tabs_with_id():
    """Test CustomTabs with ID."""
    tabs = CustomTabs(id="tabs-1")
    assert tabs.id == "tabs-1"


def test_custom_tabs_with_classes():
    """Test CustomTabs with classes."""
    tabs = CustomTabs(classes="custom-class")
    assert "custom-class" in tabs.classes


# =============================================================================
# CustomTab Tests (PRD-charts-screen-fix)
# =============================================================================


class TestCustomTabInstantiation:
    """Test CustomTab instantiation with various label types."""

    def test_basic_instantiation(self) -> None:
        """Test CustomTab can be instantiated with a string label."""
        tab = CustomTab(label="Test Tab")
        assert tab is not None

    def test_instantiation_with_id(self) -> None:
        """Test CustomTab instantiation with an ID."""
        tab = CustomTab(label="Tab", id="my-tab")
        assert tab.id == "my-tab"

    def test_instantiation_with_disabled(self) -> None:
        """Test CustomTab instantiation in disabled state."""
        tab = CustomTab(label="Disabled", disabled=True)
        assert tab.disabled is True

    def test_instantiation_with_classes(self) -> None:
        """Test CustomTab instantiation with CSS classes."""
        tab = CustomTab(label="Styled", classes="custom-class")
        assert "custom-class" in tab.classes

    def test_instantiation_with_empty_string(self) -> None:
        """Test CustomTab with empty string label (edge case E1)."""
        tab = CustomTab(label="")
        assert tab is not None
        assert tab.label_text == ""

    def test_instantiation_with_unicode_label(self) -> None:
        """Test CustomTab with unicode characters in label."""
        tab = CustomTab(label="Ubersicht")
        assert tab.label_text == "Ubersicht"

    def test_instantiation_with_special_characters(self) -> None:
        """Test CustomTab with special characters in label."""
        tab = CustomTab(label="Tab (1) - All Charts")
        assert tab.label_text == "Tab (1) - All Charts"

    def test_css_path(self) -> None:
        """Test CustomTab CSS_PATH is set correctly."""
        assert CustomTab.CSS_PATH.endswith("css/widgets/custom_tabs.tcss")


class TestCustomTabLabelText:
    """Test CustomTab.label_text property (non-conflicting accessor)."""

    def test_label_text_returns_plain_string(self) -> None:
        """Test label_text returns a plain string, not Content."""
        tab = CustomTab(label="My Tab")
        result = tab.label_text
        assert isinstance(result, str)
        assert result == "My Tab"

    def test_label_text_preserves_original_value(self) -> None:
        """Test label_text preserves the original constructor value."""
        tab = CustomTab(label="Original")
        assert tab.label_text == "Original"

    def test_label_text_empty_string(self) -> None:
        """Test label_text with empty string."""
        tab = CustomTab(label="")
        assert tab.label_text == ""

    def test_label_text_whitespace(self) -> None:
        """Test label_text with whitespace-only label."""
        tab = CustomTab(label="  spaces  ")
        assert tab.label_text == "  spaces  "


class TestCustomTabNativeLabelPassthrough:
    """Regression tests: CustomTab.label must NOT shadow TextualTab.label.

    Before the fix in PRD-charts-screen-fix, CustomTab defined a ``label``
    property that returned ``str`` and had no setter.  This shadowed
    ``TextualTab.label`` (which returns ``Content`` and has a setter),
    causing ``AttributeError`` during ``Tab.__init__()`` when Textual's
    constructor tried to set ``self.label = ...`` via the property setter.

    These tests verify that the native label property is preserved.
    """

    def test_native_label_returns_content_type(self) -> None:
        """Test that label returns Textual's Content type (T3 from handoff)."""
        tab = CustomTab(label="Test")
        assert isinstance(tab.label, Content)

    def test_native_label_string_representation(self) -> None:
        """Test that str(label) matches the original string."""
        tab = CustomTab(label="Charts Overview")
        assert str(tab.label) == "Charts Overview"

    def test_native_label_setter_works(self) -> None:
        """Test that the native label setter is accessible (not shadowed)."""
        tab = CustomTab(label="Original")
        # This would raise AttributeError if label property was read-only (old bug)
        tab.label = "Updated"
        assert str(tab.label) == "Updated"

    def test_label_property_not_defined_on_custom_tab(self) -> None:
        """Test that CustomTab does NOT define its own label property."""
        # The fix removed the shadowing property, so CustomTab.__dict__
        # should NOT contain 'label'
        assert "label" not in CustomTab.__dict__

    def test_label_inherited_from_textual_tab(self) -> None:
        """Test that label comes from TextualTab's MRO."""
        # Find which class in MRO provides the label property
        for cls in CustomTab.__mro__:
            if "label" in cls.__dict__:
                # It should be TextualTab or one of its ancestors, NOT CustomTab
                assert cls is not CustomTab
                break

    def test_custom_tab_is_subclass_of_textual_tab(self) -> None:
        """Test that CustomTab properly extends TextualTab."""
        assert issubclass(CustomTab, TextualTab)

    def test_label_and_label_text_are_different(self) -> None:
        """Test that label (Content) and label_text (str) are distinct."""
        tab = CustomTab(label="Test")
        # label returns Content
        assert isinstance(tab.label, Content)
        # label_text returns str
        assert isinstance(tab.label_text, str)
        # Both represent the same text
        assert str(tab.label) == tab.label_text


class TestCustomTabCreateTab:
    """Test CustomTabs.create_tab factory method."""

    def test_create_tab_returns_custom_tab(self) -> None:
        """Test that create_tab returns a CustomTab instance."""
        tabs = CustomTabs()
        tab = tabs.create_tab("New Tab")
        assert isinstance(tab, CustomTab)

    def test_create_tab_label_text(self) -> None:
        """Test that created tab has correct label_text."""
        tabs = CustomTabs()
        tab = tabs.create_tab("Created Tab")
        assert tab.label_text == "Created Tab"

    def test_create_tab_disabled(self) -> None:
        """Test that create_tab respects disabled flag."""
        tabs = CustomTabs()
        tab = tabs.create_tab("Disabled", disabled=True)
        assert tab.disabled is True
