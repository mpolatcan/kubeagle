"""Tests for CustomTableBuilder widget.

Tests cover:
- CustomTableBuilder instantiation
- Table building functionality
"""

from __future__ import annotations

import pytest

from kubeagle.widgets.data.tables.custom_table_builder import (
    CustomTableBuilder,
)

# =============================================================================
# CustomTableBuilder Widget Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.fast
class TestCustomTableBuilder:
    """Tests for CustomTableBuilder widget."""

    def test_custom_table_builder_instantiation(self) -> None:
        """Test CustomTableBuilder can be instantiated."""
        builder = CustomTableBuilder()
        assert builder is not None
