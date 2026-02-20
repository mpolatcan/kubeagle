"""Tests for CustomFooter widget."""

from __future__ import annotations

from kubeagle.widgets.structure.custom_footer import CustomFooter


def test_custom_footer_instantiation():
    """Test CustomFooter instantiation."""
    footer = CustomFooter()
    assert footer is not None


def test_custom_footer_css_path():
    """Test CSS path is set correctly."""
    assert getattr(CustomFooter, "CSS_PATH", "").endswith(
        "css/widgets/custom_footer.tcss"
    )


def test_custom_footer_css_property():
    """Test CustomFooter CSS property."""
    footer = CustomFooter()
    css = footer.CSS
    assert isinstance(css, str)


def test_custom_footer_exports():
    """Test CustomFooter exports."""
    from kubeagle.widgets.structure.custom_footer import __all__
    assert "CustomFooter" in __all__


def test_custom_footer_with_id():
    """Test CustomFooter with ID."""
    footer = CustomFooter(id="footer-1")
    assert footer.id == "footer-1"


def test_custom_footer_with_classes():
    """Test CustomFooter with classes."""
    footer = CustomFooter(classes="custom-class")
    assert "custom-class" in footer.classes
