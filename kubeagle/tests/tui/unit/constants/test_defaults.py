"""Unit tests for default values in constants/defaults.py.

Tests cover:
- All default value constants
- Correct types (str, int, float, bool)
- Expected specific values
- Non-empty strings where appropriate
"""

from __future__ import annotations

from kubeagle.constants.defaults import (
    ACTIVE_CHARTS_PATH_DEFAULT,
    AI_FIX_BULK_PARALLELISM_DEFAULT,
    AI_FIX_CLAUDE_MODEL_DEFAULT,
    AI_FIX_CODEX_MODEL_DEFAULT,
    AI_FIX_FULL_FIX_SYSTEM_PROMPT_DEFAULT,
    AI_FIX_LLM_PROVIDER_DEFAULT,
    AUTO_REFRESH_DEFAULT,
    CHARTS_PATH_DEFAULT,
    CODEOWNERS_PATH_DEFAULT,
    EVENT_AGE_HOURS_DEFAULT,
    EXPORT_PATH_DEFAULT,
    EXTREME_RATIOS_THRESHOLD_DEFAULT,
    HIGH_CPU_THRESHOLD_DEFAULT,
    HIGH_MEMORY_THRESHOLD_DEFAULT,
    HIGH_POD_PERCENTAGE_THRESHOLD_DEFAULT,
    HIGH_POD_THRESHOLD_DEFAULT,
    LIMIT_REQUEST_RATIO_THRESHOLD_DEFAULT,
    REFRESH_INTERVAL_DEFAULT,
    THEME_DEFAULT,
    USE_CLUSTER_MODE_DEFAULT,
    USE_CLUSTER_VALUES_DEFAULT,
)

# =============================================================================
# Path defaults
# =============================================================================


class TestPathDefaults:
    """Test path-related default values."""

    def test_charts_path_default_type(self) -> None:
        assert isinstance(CHARTS_PATH_DEFAULT, str)

    def test_charts_path_default_value(self) -> None:
        assert CHARTS_PATH_DEFAULT == ""

    def test_active_charts_path_default_type(self) -> None:
        assert isinstance(ACTIVE_CHARTS_PATH_DEFAULT, str)

    def test_active_charts_path_default_value(self) -> None:
        assert ACTIVE_CHARTS_PATH_DEFAULT == ""

    def test_codeowners_path_default_type(self) -> None:
        assert isinstance(CODEOWNERS_PATH_DEFAULT, str)

    def test_codeowners_path_default_value(self) -> None:
        assert CODEOWNERS_PATH_DEFAULT == ""

    def test_export_path_default_type(self) -> None:
        assert isinstance(EXPORT_PATH_DEFAULT, str)

    def test_export_path_default_non_empty(self) -> None:
        assert len(EXPORT_PATH_DEFAULT) > 0

    def test_export_path_default_value(self) -> None:
        assert EXPORT_PATH_DEFAULT == "./reports"


# =============================================================================
# UI defaults
# =============================================================================


class TestUIDefaults:
    """Test UI-related default values."""

    def test_theme_default_type(self) -> None:
        assert isinstance(THEME_DEFAULT, str)

    def test_theme_default_value(self) -> None:
        assert THEME_DEFAULT == "InsiderOne-Dark"

    def test_refresh_interval_default_type(self) -> None:
        assert isinstance(REFRESH_INTERVAL_DEFAULT, int)

    def test_refresh_interval_default_value(self) -> None:
        assert REFRESH_INTERVAL_DEFAULT == 30

    def test_refresh_interval_default_positive(self) -> None:
        assert REFRESH_INTERVAL_DEFAULT > 0

    def test_auto_refresh_default_type(self) -> None:
        assert isinstance(AUTO_REFRESH_DEFAULT, bool)

    def test_auto_refresh_default_value(self) -> None:
        assert AUTO_REFRESH_DEFAULT is False


# =============================================================================
# Cluster defaults
# =============================================================================


class TestClusterDefaults:
    """Test cluster-related default values."""

    def test_use_cluster_values_default_type(self) -> None:
        assert isinstance(USE_CLUSTER_VALUES_DEFAULT, bool)

    def test_use_cluster_values_default_value(self) -> None:
        assert USE_CLUSTER_VALUES_DEFAULT is False

    def test_use_cluster_mode_default_type(self) -> None:
        assert isinstance(USE_CLUSTER_MODE_DEFAULT, bool)

    def test_use_cluster_mode_default_value(self) -> None:
        assert USE_CLUSTER_MODE_DEFAULT is False


# =============================================================================
# Threshold defaults
# =============================================================================


class TestThresholdDefaults:
    """Test threshold-related default values."""

    def test_event_age_hours_default_type(self) -> None:
        assert isinstance(EVENT_AGE_HOURS_DEFAULT, float)

    def test_event_age_hours_default_value(self) -> None:
        assert EVENT_AGE_HOURS_DEFAULT == 1.0

    def test_event_age_hours_default_positive(self) -> None:
        assert EVENT_AGE_HOURS_DEFAULT > 0

    def test_high_cpu_threshold_default_type(self) -> None:
        assert isinstance(HIGH_CPU_THRESHOLD_DEFAULT, int)

    def test_high_cpu_threshold_default_value(self) -> None:
        assert HIGH_CPU_THRESHOLD_DEFAULT == 80

    def test_high_cpu_threshold_default_range(self) -> None:
        assert 1 <= HIGH_CPU_THRESHOLD_DEFAULT <= 100

    def test_high_memory_threshold_default_type(self) -> None:
        assert isinstance(HIGH_MEMORY_THRESHOLD_DEFAULT, int)

    def test_high_memory_threshold_default_value(self) -> None:
        assert HIGH_MEMORY_THRESHOLD_DEFAULT == 80

    def test_high_pod_threshold_default_type(self) -> None:
        assert isinstance(HIGH_POD_THRESHOLD_DEFAULT, int)

    def test_high_pod_threshold_default_value(self) -> None:
        assert HIGH_POD_THRESHOLD_DEFAULT == 80

    def test_limit_request_ratio_threshold_default_type(self) -> None:
        assert isinstance(LIMIT_REQUEST_RATIO_THRESHOLD_DEFAULT, float)

    def test_limit_request_ratio_threshold_default_value(self) -> None:
        assert LIMIT_REQUEST_RATIO_THRESHOLD_DEFAULT == 2.0

    def test_limit_request_ratio_threshold_default_positive(self) -> None:
        assert LIMIT_REQUEST_RATIO_THRESHOLD_DEFAULT > 0

    def test_high_pod_percentage_threshold_default_type(self) -> None:
        assert isinstance(HIGH_POD_PERCENTAGE_THRESHOLD_DEFAULT, int)

    def test_high_pod_percentage_threshold_default_value(self) -> None:
        assert HIGH_POD_PERCENTAGE_THRESHOLD_DEFAULT == 80

    def test_extreme_ratios_threshold_default_type(self) -> None:
        assert isinstance(EXTREME_RATIOS_THRESHOLD_DEFAULT, float)

    def test_extreme_ratios_threshold_default_value(self) -> None:
        assert EXTREME_RATIOS_THRESHOLD_DEFAULT == 2.0

    def test_extreme_ratios_threshold_default_positive(self) -> None:
        assert EXTREME_RATIOS_THRESHOLD_DEFAULT > 0


class TestOptimizerVerificationDefaults:
    """Test optimizer verification default values."""

    def test_ai_fix_llm_provider_default_type(self) -> None:
        assert isinstance(AI_FIX_LLM_PROVIDER_DEFAULT, str)

    def test_ai_fix_llm_provider_default_value(self) -> None:
        assert AI_FIX_LLM_PROVIDER_DEFAULT == "codex"

    def test_ai_fix_codex_model_default_type(self) -> None:
        assert isinstance(AI_FIX_CODEX_MODEL_DEFAULT, str)

    def test_ai_fix_codex_model_default_value(self) -> None:
        assert AI_FIX_CODEX_MODEL_DEFAULT == "auto"

    def test_ai_fix_claude_model_default_type(self) -> None:
        assert isinstance(AI_FIX_CLAUDE_MODEL_DEFAULT, str)

    def test_ai_fix_claude_model_default_value(self) -> None:
        assert AI_FIX_CLAUDE_MODEL_DEFAULT == "auto"

    def test_ai_fix_full_fix_system_prompt_default(self) -> None:
        assert AI_FIX_FULL_FIX_SYSTEM_PROMPT_DEFAULT == ""

    def test_ai_fix_bulk_parallelism_default(self) -> None:
        assert AI_FIX_BULK_PARALLELISM_DEFAULT == 2


# =============================================================================
# __all__ exports
# =============================================================================


class TestDefaultsExports:
    """Test that __all__ exports are correct."""

    def test_all_exports_importable(self) -> None:
        import kubeagle.constants.defaults as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"{name} listed in __all__ but not defined"
