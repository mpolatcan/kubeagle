"""Tests for CustomFooter widget implementation.

Tests cover:
- CustomFooter widget creation and composition
- CustomFooter inherits from TextualFooter for binding discovery
- CSS styling and docking behavior
- BaseScreen integration with CustomFooter

The fix (fix-01) changed CustomFooter to inherit from TextualFooter instead of
Container/StatefulWidget for automatic binding discovery.
"""

from __future__ import annotations

import pytest
from textual.widgets import Footer as TextualFooter
from textual.widgets._footer import FooterKey

from kubeagle.widgets import CustomFooter

# =============================================================================
# CustomFooter Widget Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.fast
class TestCustomFooter:
    """Tests for CustomFooter widget."""

    def test_custom_footer_inherits_textual_footer(self) -> None:
        """Test CustomFooter inherits from TextualFooter."""
        footer = CustomFooter()
        assert isinstance(footer, TextualFooter)

    def test_custom_footer_has_default_css(self) -> None:
        """Test CustomFooter has DEFAULT_CSS with theme-compatible tokens."""
        assert "$footer-background" in CustomFooter.DEFAULT_CSS
        assert "$footer-foreground" in CustomFooter.DEFAULT_CSS
        assert "dock: bottom" in CustomFooter.DEFAULT_CSS

    def test_custom_footer_widget_class_name(self) -> None:
        """Test CustomFooter widget class name is available."""
        footer = CustomFooter()
        assert "CustomFooter" in type(footer).__name__

    def test_custom_footer_all_exports(self) -> None:
        """Test CustomFooter is in __all__ exports."""
        from kubeagle.widgets import __all__

        assert "CustomFooter" in __all__


# =============================================================================
# CustomFooter Integration Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestCustomFooterIntegration:
    """Integration tests for CustomFooter with screens."""

    async def test_primary_screen_has_footer(self) -> None:
        """Test that the initial cluster screen has a CustomFooter widget."""
        from kubeagle.app import EKSHelmReporterApp

        app = EKSHelmReporterApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            # Query for CustomFooter widget in the current screen
            footers = app.screen.query("CustomFooter")
            assert len(footers) > 0, "Screen should contain a CustomFooter widget"

    async def test_footer_renders_binding_descriptions(self) -> None:
        """Test footer shows binding labels, not only key names."""
        from kubeagle.app import EKSHelmReporterApp

        app = EKSHelmReporterApp()
        async with app.run_test(size=(120, 24)) as pilot:
            await pilot.pause()
            footer = app.screen.query_one("CustomFooter")
            footer_keys = list(footer.query(FooterKey))
            descriptions = {key.description for key in footer_keys}
            assert "Cluster" in descriptions
            assert "Settings" in descriptions

    async def test_footer_uses_default_textual_scroll_on_narrow_width(self) -> None:
        """Test narrow layouts do not render custom Prev/Next footer controls."""
        from kubeagle.app import EKSHelmReporterApp

        app = EKSHelmReporterApp()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            footer = app.screen.query_one("CustomFooter")
            footer_keys = list(footer.query(FooterKey))
            descriptions = {key.description for key in footer_keys}
            assert "Prev" not in descriptions
            assert "Next" not in descriptions
