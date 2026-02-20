"""Tests for CustomCard container widget.

Tests cover:
- CustomCard instantiation
- Title handling
"""

from __future__ import annotations

import pytest

from kubeagle.widgets.containers.custom_card import CustomCard

# =============================================================================
# CustomCard Widget Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.fast
class TestCustomCard:
    """Tests for CustomCard widget."""

    def test_custom_card_instantiation(self) -> None:
        """Test CustomCard can be instantiated."""
        card = CustomCard()
        assert card is not None

    def test_custom_card_with_title(self) -> None:
        """Test CustomCard with title."""
        card = CustomCard(title="Test Title")
        assert card.card_title == "Test Title"

    def test_custom_card_empty_title_default(self) -> None:
        """Test CustomCard has empty title by default."""
        card = CustomCard()
        assert card.card_title == ""

    def test_custom_card_set_title_method(self) -> None:
        """Test set_title method exists."""
        card = CustomCard()
        assert hasattr(card, "set_title")
        assert callable(card.set_title)

    def test_custom_card_card_title_property(self) -> None:
        """Test card_title property exists."""
        card = CustomCard()
        assert hasattr(card, "card_title")

    def test_custom_card_with_id(self) -> None:
        """Test CustomCard with custom ID."""
        card = CustomCard(id="my-card")
        assert card.id == "my-card"

    def test_custom_card_with_classes(self) -> None:
        """Test CustomCard with custom CSS classes."""
        card = CustomCard(classes="custom another")
        assert "custom" in card.classes
        assert "another" in card.classes
