"""Settings screen constants."""

from typing import Final

# ============================================================================
# Section headers
# ============================================================================

SETTINGS_SECTION_GENERAL: Final = "General Settings"
SETTINGS_SECTION_THRESHOLDS: Final = "Threshold Settings"
SETTINGS_SECTION_AI_FIX: Final = "AI Fix Settings"
SETTINGS_SECTION_CLUSTER: Final = "Cluster Settings"

# ============================================================================
# Validation messages
# ============================================================================

SETTINGS_VALIDATION_MESSAGES: dict[str, tuple[str, int | float]] = {
    "refresh_interval_min": ("Refresh interval must be at least 5 seconds. Using 30.", 30),
    "refresh_interval_invalid": ("Refresh interval must be at least 5 seconds.", 30),
    "theme_invalid": ("Invalid theme '{theme}'. Using 'dark'.", 0),
    "cpu_threshold_range": ("High CPU threshold must be between 1-100. Using 80.", 80),
    "memory_threshold_range": ("High Memory threshold must be between 1-100. Using 80.", 80),
    "pod_threshold_range": ("High Pod threshold must be between 1-100. Using 80.", 80),
    "pod_percent_threshold_range": ("High Pod Percentage threshold must be between 1-100. Using 80.", 80),
    "event_age_invalid": ("Event age filter must be positive. Using 1.0.", 1.0),
    "limit_request_invalid": ("Limit/Request ratio threshold must be positive. Using 3.0.", 3.0),
    "charts_path_invalid": ("Invalid charts path: '{path}'. Path must exist and be a directory.", 0),
    "active_charts_invalid": ("Invalid active charts file: '{path}'. Path must be a file.", 0),
}

# ============================================================================
# Success messages
# ============================================================================

SETTINGS_SAVE_SUCCESS: Final = "Settings saved successfully!"

# ============================================================================
# Action buttons
# ============================================================================

BUTTON_SAVE: Final = "Save"
BUTTON_CANCEL: Final = "Cancel"

# ============================================================================
# Screen title
# ============================================================================

SETTINGS_SCREEN_TITLE: Final = "KubEagle - Settings"

__all__ = [
    "SETTINGS_SECTION_GENERAL",
    "SETTINGS_SECTION_THRESHOLDS",
    "SETTINGS_SECTION_AI_FIX",
    "SETTINGS_SECTION_CLUSTER",
    "SETTINGS_VALIDATION_MESSAGES",
    "SETTINGS_SAVE_SUCCESS",
    "BUTTON_SAVE",
    "BUTTON_CANCEL",
    "SETTINGS_SCREEN_TITLE",
]
