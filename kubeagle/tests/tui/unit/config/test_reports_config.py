"""Unit tests for Reports screen configuration constants.

This module tests:
- Report format/type/output option lists
- Default value constants

All constants are imported from screens.reports.config.
"""

from __future__ import annotations

from kubeagle.screens.reports.config import (
    DEFAULT_FILENAME,
    DEFAULT_REPORT_FORMAT,
    DEFAULT_REPORT_TYPE,
    REPORT_FORMATS,
    REPORT_TYPES,
)

# =============================================================================
# Report Format/Type/Output Tests
# =============================================================================


class TestReportsConfigFormats:
    """Test reports config format, type, and output option lists."""

    def test_report_formats_count(self) -> None:
        """Test REPORT_FORMATS has 3 items."""
        assert len(REPORT_FORMATS) == 3

    def test_report_formats_expected_values(self) -> None:
        """Test REPORT_FORMATS contains expected values."""
        assert "full" in REPORT_FORMATS
        assert "brief" in REPORT_FORMATS
        assert "summary" in REPORT_FORMATS

    def test_report_formats_all_strings(self) -> None:
        """Test all REPORT_FORMATS entries are non-empty strings."""
        for fmt in REPORT_FORMATS:
            assert isinstance(fmt, str)
            assert len(fmt) > 0

    def test_report_types_count(self) -> None:
        """Test REPORT_TYPES has 3 items."""
        assert len(REPORT_TYPES) == 3

    def test_report_types_expected_values(self) -> None:
        """Test REPORT_TYPES contains expected values."""
        assert "eks" in REPORT_TYPES
        assert "charts" in REPORT_TYPES
        assert "combined" in REPORT_TYPES

    def test_report_types_all_strings(self) -> None:
        """Test all REPORT_TYPES entries are non-empty strings."""
        for rt in REPORT_TYPES:
            assert isinstance(rt, str)
            assert len(rt) > 0


# =============================================================================
# Default Value Tests
# =============================================================================


class TestReportsConfigDefaults:
    """Test reports config default value constants."""

    def test_default_report_format_value(self) -> None:
        """Test DEFAULT_REPORT_FORMAT has expected value."""
        assert DEFAULT_REPORT_FORMAT == "full"

    def test_default_report_format_in_formats(self) -> None:
        """Test DEFAULT_REPORT_FORMAT is in REPORT_FORMATS."""
        assert DEFAULT_REPORT_FORMAT in REPORT_FORMATS

    def test_default_report_type_value(self) -> None:
        """Test DEFAULT_REPORT_TYPE has expected value."""
        assert DEFAULT_REPORT_TYPE == "combined"

    def test_default_report_type_in_types(self) -> None:
        """Test DEFAULT_REPORT_TYPE is in REPORT_TYPES."""
        assert DEFAULT_REPORT_TYPE in REPORT_TYPES

    def test_default_filename_value(self) -> None:
        """Test DEFAULT_FILENAME has expected value."""
        assert DEFAULT_FILENAME == "eks-helm-report.md"

    def test_default_filename_is_string(self) -> None:
        """Test DEFAULT_FILENAME is a non-empty string."""
        assert isinstance(DEFAULT_FILENAME, str)
        assert len(DEFAULT_FILENAME) > 0

    def test_default_filename_has_extension(self) -> None:
        """Test DEFAULT_FILENAME has a file extension."""
        assert "." in DEFAULT_FILENAME


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "TestReportsConfigFormats",
    "TestReportsConfigDefaults",
]
