"""Tests for CustomContainer widgets.

Tests cover:
- CustomContainer instantiation
- CustomHorizontal instantiation
- CustomVertical instantiation
"""

from __future__ import annotations

import pytest

from kubeagle.widgets.containers.custom_containers import (
    CustomContainer,
    CustomHorizontal,
    CustomVertical,
)

# =============================================================================
# CustomContainer Widget Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.fast
class TestCustomContainer:
    """Tests for CustomContainer widget."""

    def test_custom_container_instantiation(self) -> None:
        """Test CustomContainer can be instantiated."""
        container = CustomContainer()
        assert container is not None

    def test_custom_container_with_id(self) -> None:
        """Test CustomContainer with custom ID."""
        container = CustomContainer(id="my-container")
        assert container.id == "my-container"

    def test_custom_container_with_classes(self) -> None:
        """Test CustomContainer with custom CSS classes."""
        container = CustomContainer(classes="custom")
        assert "custom" in container.classes


# =============================================================================
# CustomHorizontal Widget Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.fast
class TestCustomHorizontal:
    """Tests for CustomHorizontal widget."""

    def test_custom_horizontal_instantiation(self) -> None:
        """Test CustomHorizontal can be instantiated."""
        horizontal = CustomHorizontal()
        assert horizontal is not None

    def test_custom_horizontal_with_id(self) -> None:
        """Test CustomHorizontal with custom ID."""
        horizontal = CustomHorizontal(id="my-horizontal")
        assert horizontal.id == "my-horizontal"


# =============================================================================
# CustomVertical Widget Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.fast
class TestCustomVertical:
    """Tests for CustomVertical widget."""

    def test_custom_vertical_instantiation(self) -> None:
        """Test CustomVertical can be instantiated."""
        vertical = CustomVertical()
        assert vertical is not None

    def test_custom_vertical_with_id(self) -> None:
        """Test CustomVertical with custom ID."""
        vertical = CustomVertical(id="my-vertical")
        assert vertical.id == "my-vertical"
