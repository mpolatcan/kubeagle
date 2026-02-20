"""Unit tests for widget configuration utilities in widgets/_config.py.

Tests cover:
- WidgetCategory enum
- WidgetConfig class: ID generation, class composition, status/severity helpers
- WidgetRegistry class: register, get, unregister, list_by_category
- Global instances (WIDGET_CONFIG, WIDGET_REGISTRY)
"""

from __future__ import annotations

from enum import Enum

from kubeagle.widgets._config import (
    WIDGET_CONFIG,
    WIDGET_REGISTRY,
    WidgetCategory,
    WidgetConfig,
    WidgetRegistry,
)

# =============================================================================
# WidgetCategory enum
# =============================================================================


class TestWidgetCategory:
    """Test WidgetCategory enum."""

    def test_is_enum(self) -> None:
        assert issubclass(WidgetCategory, Enum)

    def test_member_count(self) -> None:
        assert len(WidgetCategory) == 6

    def test_data_display_exists(self) -> None:
        assert hasattr(WidgetCategory, "DATA_DISPLAY")

    def test_feedback_exists(self) -> None:
        assert hasattr(WidgetCategory, "FEEDBACK")

    def test_filter_exists(self) -> None:
        assert hasattr(WidgetCategory, "FILTER")

    def test_dialog_exists(self) -> None:
        assert hasattr(WidgetCategory, "DIALOG")

    def test_navigation_exists(self) -> None:
        assert hasattr(WidgetCategory, "NAVIGATION")

    def test_layout_exists(self) -> None:
        assert hasattr(WidgetCategory, "LAYOUT")

    def test_all_members_distinct(self) -> None:
        values = [m.value for m in WidgetCategory]
        assert len(values) == len(set(values))


# =============================================================================
# WidgetConfig class variables
# =============================================================================


class TestWidgetConfigClassVars:
    """Test WidgetConfig class-level configuration."""

    def test_id_patterns_is_dict(self) -> None:
        assert isinstance(WidgetConfig.ID_PATTERNS, dict)

    def test_id_patterns_has_expected_keys(self) -> None:
        expected_keys = {"kpi", "card", "button", "input", "dialog", "table",
                         "filter", "toast", "spinner", "progress"}
        assert set(WidgetConfig.ID_PATTERNS.keys()) == expected_keys

    def test_id_patterns_values_contain_uuid(self) -> None:
        for pattern_name, pattern in WidgetConfig.ID_PATTERNS.items():
            assert "{uuid}" in pattern, f"Pattern {pattern_name} must contain {{uuid}}"

    def test_class_prefixes_is_dict(self) -> None:
        assert isinstance(WidgetConfig.CLASS_PREFIXES, dict)

    def test_class_prefixes_non_empty(self) -> None:
        assert len(WidgetConfig.CLASS_PREFIXES) > 0

    def test_class_prefixes_expected_keys(self) -> None:
        expected = {"widget", "container", "interactive", "loading", "error",
                    "success", "warning", "muted", "accent", "primary", "secondary"}
        assert set(WidgetConfig.CLASS_PREFIXES.keys()) == expected

    def test_theme_colors_is_dict(self) -> None:
        assert isinstance(WidgetConfig.THEME_COLORS, dict)

    def test_theme_colors_non_empty(self) -> None:
        assert len(WidgetConfig.THEME_COLORS) > 0

    def test_theme_colors_expected_keys(self) -> None:
        expected = {"success", "error", "warning", "info", "muted", "primary", "secondary"}
        assert set(WidgetConfig.THEME_COLORS.keys()) == expected

    def test_theme_colors_values_start_with_dollar(self) -> None:
        for key, value in WidgetConfig.THEME_COLORS.items():
            assert value.startswith("$"), f"Theme color {key} must start with $"


# =============================================================================
# WidgetConfig.generate_id
# =============================================================================


class TestWidgetConfigGenerateId:
    """Test WidgetConfig.generate_id method."""

    def test_generate_id_returns_string(self) -> None:
        config = WidgetConfig()
        result = config.generate_id("card", name="test")
        assert isinstance(result, str)

    def test_generate_id_with_card_pattern(self) -> None:
        config = WidgetConfig()
        result = config.generate_id("card", name="mycard")
        assert result.startswith("card-mycard-")

    def test_generate_id_with_kpi_pattern(self) -> None:
        config = WidgetConfig()
        result = config.generate_id("kpi", title="stats")
        assert result.startswith("kpi-stats-")

    def test_generate_id_with_button_pattern(self) -> None:
        config = WidgetConfig()
        result = config.generate_id("button", name="submit")
        assert result.startswith("btn-submit-")

    def test_generate_id_with_unknown_pattern(self) -> None:
        config = WidgetConfig()
        result = config.generate_id("unknown", name="test")
        assert result.startswith("widget-test-")

    def test_generate_id_preserves_explicit_name_kwarg(self) -> None:
        """kwargs override the default lowercased name in context."""
        config = WidgetConfig()
        result = config.generate_id("card", name="MyCard")
        # **kwargs override the default lowercased "name" key
        assert "MyCard" in result

    def test_generate_id_preserves_spaces_in_name(self) -> None:
        """kwargs override the default space-replaced name in context."""
        config = WidgetConfig()
        result = config.generate_id("card", name="my card")
        # **kwargs override the default space-replaced "name" key
        assert "my card" in result

    def test_generate_id_unique_each_call(self) -> None:
        config = WidgetConfig()
        id1 = config.generate_id("card", name="test")
        id2 = config.generate_id("card", name="test")
        assert id1 != id2


# =============================================================================
# WidgetConfig.compose_classes
# =============================================================================


class TestWidgetConfigComposeClasses:
    """Test WidgetConfig.compose_classes method."""

    def test_single_class(self) -> None:
        config = WidgetConfig()
        result = config.compose_classes("active")
        assert result == "active"

    def test_multiple_classes(self) -> None:
        config = WidgetConfig()
        result = config.compose_classes("card", "highlighted", "dark")
        assert result == "card highlighted dark"

    def test_with_prefix(self) -> None:
        config = WidgetConfig()
        result = config.compose_classes("active", "selected", prefix="state")
        assert result == "state-active state-selected"

    def test_empty_names_filtered(self) -> None:
        config = WidgetConfig()
        result = config.compose_classes("active", "", "selected")
        assert result == "active selected"

    def test_no_classes(self) -> None:
        config = WidgetConfig()
        result = config.compose_classes()
        assert result == ""

    def test_all_empty_classes(self) -> None:
        config = WidgetConfig()
        result = config.compose_classes("", "", "")
        assert result == ""


# =============================================================================
# WidgetConfig.status_class
# =============================================================================


class TestWidgetConfigStatusClass:
    """Test WidgetConfig.status_class method."""

    def test_success_status(self) -> None:
        config = WidgetConfig()
        assert config.status_class("success") == "status-success"

    def test_error_status(self) -> None:
        config = WidgetConfig()
        assert config.status_class("error") == "status-error"

    def test_warning_status(self) -> None:
        config = WidgetConfig()
        assert config.status_class("warning") == "status-warning"

    def test_uppercase_lowered(self) -> None:
        config = WidgetConfig()
        assert config.status_class("SUCCESS") == "status-success"


# =============================================================================
# WidgetConfig.severity_class
# =============================================================================


class TestWidgetConfigSeverityClass:
    """Test WidgetConfig.severity_class method."""

    def test_critical_severity(self) -> None:
        config = WidgetConfig()
        assert config.severity_class("critical") == "severity-critical"

    def test_high_severity(self) -> None:
        config = WidgetConfig()
        assert config.severity_class("high") == "severity-high"

    def test_medium_severity(self) -> None:
        config = WidgetConfig()
        assert config.severity_class("medium") == "severity-medium"

    def test_low_severity(self) -> None:
        config = WidgetConfig()
        assert config.severity_class("low") == "severity-low"

    def test_uppercase_lowered(self) -> None:
        config = WidgetConfig()
        assert config.severity_class("CRITICAL") == "severity-critical"


# =============================================================================
# WidgetRegistry
# =============================================================================


class TestWidgetRegistry:
    """Test WidgetRegistry class."""

    def test_new_registry_is_empty(self) -> None:
        registry = WidgetRegistry()
        assert registry._instances == {}
        assert registry._configs == {}

    def test_register_widget(self) -> None:
        registry = WidgetRegistry()
        obj = object()
        registry.register("widget-1", obj)
        assert registry.get("widget-1") is obj

    def test_register_with_config(self) -> None:
        registry = WidgetRegistry()
        obj = object()
        config = {"theme": "dark"}
        registry.register("widget-1", obj, config=config)
        assert registry._configs["widget-1"] == config

    def test_register_without_config(self) -> None:
        registry = WidgetRegistry()
        registry.register("widget-1", object())
        assert "widget-1" not in registry._configs

    def test_get_nonexistent_returns_none(self) -> None:
        registry = WidgetRegistry()
        assert registry.get("nonexistent") is None

    def test_unregister_widget(self) -> None:
        registry = WidgetRegistry()
        obj = object()
        registry.register("widget-1", obj, config={"test": True})
        registry.unregister("widget-1")
        assert registry.get("widget-1") is None
        assert "widget-1" not in registry._configs

    def test_unregister_nonexistent_does_not_raise(self) -> None:
        registry = WidgetRegistry()
        registry.unregister("nonexistent")  # Should not raise

    def test_list_by_category(self) -> None:
        registry = WidgetRegistry()
        registry.register("w1", object())
        registry.register("w2", object())
        result = registry.list_by_category(WidgetCategory.DATA_DISPLAY)
        assert "w1" in result
        assert "w2" in result

    def test_multiple_registrations(self) -> None:
        registry = WidgetRegistry()
        obj1 = object()
        obj2 = object()
        registry.register("w1", obj1)
        registry.register("w2", obj2)
        assert registry.get("w1") is obj1
        assert registry.get("w2") is obj2

    def test_overwrite_registration(self) -> None:
        registry = WidgetRegistry()
        obj1 = object()
        obj2 = object()
        registry.register("w1", obj1)
        registry.register("w1", obj2)
        assert registry.get("w1") is obj2


# =============================================================================
# Global instances
# =============================================================================


class TestGlobalInstances:
    """Test module-level global instances."""

    def test_widget_config_is_widget_config(self) -> None:
        assert isinstance(WIDGET_CONFIG, WidgetConfig)

    def test_widget_registry_is_widget_registry(self) -> None:
        assert isinstance(WIDGET_REGISTRY, WidgetRegistry)
