"""Unit tests for scalar constants in constants/values.py.

Tests cover:
- Application constants
- Color constants (hex format)
- Layout constants
- Data constants
- Caching constants
- Status strings
- Health status markup
- Placeholder strings
- Error/status messages
"""

from __future__ import annotations

import re

from kubeagle.constants.values import (
    APP_TITLE,
    COLOR_ACCENT,
    COLOR_ERROR,
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    COLOR_SUCCESS,
    COLOR_WARNING,
    DEGRADED,
    HEALTHY,
    MAX_CACHE_AGE_SECONDS,
    MSG_CLUSTER_CONNECTION_FAILED,
    MSG_CLUSTER_NAME_DEFAULT,
    MSG_INITIALIZING,
    MSG_LOADING,
    MSG_NEVER,
    MSG_OPERATION_CANCELLED,
    MSG_UNKNOWN,
    PLACEHOLDER_ACTIVE_CHARTS,
    PLACEHOLDER_CHARTS_PATH,
    PLACEHOLDER_CODEOWNERS,
    PLACEHOLDER_EVENT_AGE,
    PLACEHOLDER_EXPORT_PATH,
    PLACEHOLDER_LIMIT_REQUEST,
    PLACEHOLDER_REFRESH_INTERVAL,
    PLACEHOLDER_THRESHOLD,
    SPACING,
    STATUS_CONNECTED,
    STATUS_DISCONNECTED,
    STATUS_LOADING,
    TABLE_PAGE_SIZE,
    UNHEALTHY,
)

# =============================================================================
# Application
# =============================================================================


class TestApplicationConstants:
    """Test application-level constants."""

    def test_app_title_type(self) -> None:
        assert isinstance(APP_TITLE, str)

    def test_app_title_value(self) -> None:
        assert APP_TITLE == "KubEagle"

    def test_app_title_non_empty(self) -> None:
        assert len(APP_TITLE) > 0


# =============================================================================
# Colors
# =============================================================================


HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")

ALL_COLORS = [
    ("COLOR_PRIMARY", COLOR_PRIMARY, "#007ACC"),
    ("COLOR_SECONDARY", COLOR_SECONDARY, "#6C757D"),
    ("COLOR_ACCENT", COLOR_ACCENT, "#17A2B8"),
    ("COLOR_SUCCESS", COLOR_SUCCESS, "#28A745"),
    ("COLOR_WARNING", COLOR_WARNING, "#FFC107"),
    ("COLOR_ERROR", COLOR_ERROR, "#DC3545"),
]


class TestColorConstants:
    """Test color hex string constants."""

    def test_color_primary_value(self) -> None:
        assert COLOR_PRIMARY == "#007ACC"

    def test_color_secondary_value(self) -> None:
        assert COLOR_SECONDARY == "#6C757D"

    def test_color_accent_value(self) -> None:
        assert COLOR_ACCENT == "#17A2B8"

    def test_color_success_value(self) -> None:
        assert COLOR_SUCCESS == "#28A745"

    def test_color_warning_value(self) -> None:
        assert COLOR_WARNING == "#FFC107"

    def test_color_error_value(self) -> None:
        assert COLOR_ERROR == "#DC3545"

    def test_all_colors_are_strings(self) -> None:
        for name, color, _ in ALL_COLORS:
            assert isinstance(color, str), f"{name} must be a string"

    def test_all_colors_are_valid_hex(self) -> None:
        for name, color, _ in ALL_COLORS:
            assert HEX_COLOR_PATTERN.match(color), f"{name} ({color}) must be valid hex #RRGGBB"


# =============================================================================
# Layout
# =============================================================================


class TestLayoutConstants:
    """Test layout-related constants."""

    def test_spacing_type(self) -> None:
        assert isinstance(SPACING, int)

    def test_spacing_value(self) -> None:
        assert SPACING == 1

    def test_spacing_non_negative(self) -> None:
        assert SPACING >= 0


# =============================================================================
# Data
# =============================================================================


class TestDataConstants:
    """Test data-related constants."""

    def test_table_page_size_type(self) -> None:
        assert isinstance(TABLE_PAGE_SIZE, int)

    def test_table_page_size_value(self) -> None:
        assert TABLE_PAGE_SIZE == 50

    def test_table_page_size_positive(self) -> None:
        assert TABLE_PAGE_SIZE > 0


# =============================================================================
# Caching
# =============================================================================


class TestCachingConstants:
    """Test caching-related constants."""

    def test_max_cache_age_seconds_type(self) -> None:
        assert isinstance(MAX_CACHE_AGE_SECONDS, int)

    def test_max_cache_age_seconds_value(self) -> None:
        assert MAX_CACHE_AGE_SECONDS == 300

    def test_max_cache_age_seconds_positive(self) -> None:
        assert MAX_CACHE_AGE_SECONDS > 0


# =============================================================================
# Status strings
# =============================================================================


class TestStatusStrings:
    """Test status string constants."""

    def test_status_disconnected_type(self) -> None:
        assert isinstance(STATUS_DISCONNECTED, str)

    def test_status_disconnected_value(self) -> None:
        assert STATUS_DISCONNECTED == "Disconnected"

    def test_status_connected_type(self) -> None:
        assert isinstance(STATUS_CONNECTED, str)

    def test_status_connected_value(self) -> None:
        assert STATUS_CONNECTED == "Connected"

    def test_status_loading_type(self) -> None:
        assert isinstance(STATUS_LOADING, str)

    def test_status_loading_value(self) -> None:
        assert STATUS_LOADING == "Loading..."


# =============================================================================
# Health status markup
# =============================================================================


class TestHealthStatusMarkup:
    """Test health status rich text markup constants."""

    def test_healthy_type(self) -> None:
        assert isinstance(HEALTHY, str)

    def test_healthy_contains_green(self) -> None:
        assert "[green]" in HEALTHY

    def test_healthy_contains_healthy(self) -> None:
        assert "HEALTHY" in HEALTHY

    def test_degraded_type(self) -> None:
        assert isinstance(DEGRADED, str)

    def test_degraded_contains_yellow(self) -> None:
        assert "[yellow]" in DEGRADED

    def test_degraded_contains_degraded(self) -> None:
        assert "DEGRADED" in DEGRADED

    def test_unhealthy_type(self) -> None:
        assert isinstance(UNHEALTHY, str)

    def test_unhealthy_contains_red(self) -> None:
        assert "[red]" in UNHEALTHY

    def test_unhealthy_contains_unhealthy(self) -> None:
        assert "UNHEALTHY" in UNHEALTHY


# =============================================================================
# Placeholders
# =============================================================================


class TestPlaceholderConstants:
    """Test settings screen placeholder constants."""

    def test_placeholder_charts_path_type(self) -> None:
        assert isinstance(PLACEHOLDER_CHARTS_PATH, str)

    def test_placeholder_charts_path_non_empty(self) -> None:
        assert len(PLACEHOLDER_CHARTS_PATH) > 0

    def test_placeholder_active_charts_type(self) -> None:
        assert isinstance(PLACEHOLDER_ACTIVE_CHARTS, str)

    def test_placeholder_codeowners_type(self) -> None:
        assert isinstance(PLACEHOLDER_CODEOWNERS, str)

    def test_placeholder_refresh_interval_type(self) -> None:
        assert isinstance(PLACEHOLDER_REFRESH_INTERVAL, str)

    def test_placeholder_export_path_type(self) -> None:
        assert isinstance(PLACEHOLDER_EXPORT_PATH, str)

    def test_placeholder_event_age_type(self) -> None:
        assert isinstance(PLACEHOLDER_EVENT_AGE, str)

    def test_placeholder_threshold_type(self) -> None:
        assert isinstance(PLACEHOLDER_THRESHOLD, str)

    def test_placeholder_limit_request_type(self) -> None:
        assert isinstance(PLACEHOLDER_LIMIT_REQUEST, str)

    def test_all_placeholders_non_empty(self) -> None:
        placeholders = [
            PLACEHOLDER_CHARTS_PATH,
            PLACEHOLDER_ACTIVE_CHARTS,
            PLACEHOLDER_CODEOWNERS,
            PLACEHOLDER_REFRESH_INTERVAL,
            PLACEHOLDER_EXPORT_PATH,
            PLACEHOLDER_EVENT_AGE,
            PLACEHOLDER_THRESHOLD,
            PLACEHOLDER_LIMIT_REQUEST,
        ]
        for p in placeholders:
            assert len(p) > 0, f"Placeholder must not be empty: {p!r}"


# =============================================================================
# Error and status messages
# =============================================================================


class TestMessageConstants:
    """Test error and status message constants."""

    def test_msg_cluster_connection_failed_type(self) -> None:
        assert isinstance(MSG_CLUSTER_CONNECTION_FAILED, str)

    def test_msg_cluster_connection_failed_non_empty(self) -> None:
        assert len(MSG_CLUSTER_CONNECTION_FAILED) > 0

    def test_msg_operation_cancelled_type(self) -> None:
        assert isinstance(MSG_OPERATION_CANCELLED, str)

    def test_msg_initializing_type(self) -> None:
        assert isinstance(MSG_INITIALIZING, str)

    def test_msg_loading_type(self) -> None:
        assert isinstance(MSG_LOADING, str)

    def test_msg_cluster_name_default_type(self) -> None:
        assert isinstance(MSG_CLUSTER_NAME_DEFAULT, str)

    def test_msg_unknown_type(self) -> None:
        assert isinstance(MSG_UNKNOWN, str)

    def test_msg_unknown_value(self) -> None:
        assert MSG_UNKNOWN == "Unknown"

    def test_msg_never_type(self) -> None:
        assert isinstance(MSG_NEVER, str)

    def test_msg_never_value(self) -> None:
        assert MSG_NEVER == "Never"


# =============================================================================
# __all__ exports
# =============================================================================


class TestValuesExports:
    """Test that __all__ exports are correct."""

    def test_all_exports_importable(self) -> None:
        import kubeagle.constants.values as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"{name} listed in __all__ but not defined"
