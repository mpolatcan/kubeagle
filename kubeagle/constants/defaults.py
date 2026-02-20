"""Default values for settings.

All default values used in AppSettings model and validation fallback values.
"""

from typing import Final

# ============================================================================
# Path defaults
# ============================================================================

CHARTS_PATH_DEFAULT: Final = ""
ACTIVE_CHARTS_PATH_DEFAULT: Final = ""
CODEOWNERS_PATH_DEFAULT: Final = ""
EXPORT_PATH_DEFAULT: Final = "./reports"

# ============================================================================
# UI defaults
# ============================================================================

THEME_DEFAULT: Final = "InsiderOne-Dark"
REFRESH_INTERVAL_DEFAULT: Final = 30
AUTO_REFRESH_DEFAULT: Final = False

# ============================================================================
# Cluster defaults
# ============================================================================

USE_CLUSTER_VALUES_DEFAULT: Final = False
USE_CLUSTER_MODE_DEFAULT: Final = False

# ============================================================================
# Threshold defaults
# ============================================================================

EVENT_AGE_HOURS_DEFAULT: Final = 1.0
HIGH_CPU_THRESHOLD_DEFAULT: Final = 80
HIGH_MEMORY_THRESHOLD_DEFAULT: Final = 80
HIGH_POD_THRESHOLD_DEFAULT: Final = 80
LIMIT_REQUEST_RATIO_THRESHOLD_DEFAULT: Final = 2.0
HIGH_POD_PERCENTAGE_THRESHOLD_DEFAULT: Final = 80

# ============================================================================
# Optimizer verification defaults
# ============================================================================

OPTIMIZER_ANALYSIS_SOURCE_DEFAULT: Final = "auto"
VERIFY_FIXES_WITH_RENDER_DEFAULT: Final = True
HELM_TEMPLATE_TIMEOUT_SECONDS_DEFAULT: Final = 30
AI_FIX_LLM_PROVIDER_DEFAULT: Final = "codex"
AI_FIX_CODEX_MODEL_DEFAULT: Final = "auto"
AI_FIX_CLAUDE_MODEL_DEFAULT: Final = "auto"
AI_FIX_FULL_FIX_SYSTEM_PROMPT_DEFAULT: Final = ""
AI_FIX_BULK_PARALLELISM_DEFAULT: Final = 2

# ============================================================================
# Charts screen defaults
# ============================================================================

EXTREME_RATIOS_THRESHOLD_DEFAULT: Final = 2.0

__all__ = [
    "CHARTS_PATH_DEFAULT",
    "ACTIVE_CHARTS_PATH_DEFAULT",
    "CODEOWNERS_PATH_DEFAULT",
    "EXPORT_PATH_DEFAULT",
    "THEME_DEFAULT",
    "REFRESH_INTERVAL_DEFAULT",
    "AUTO_REFRESH_DEFAULT",
    "USE_CLUSTER_VALUES_DEFAULT",
    "USE_CLUSTER_MODE_DEFAULT",
    "EVENT_AGE_HOURS_DEFAULT",
    "HIGH_CPU_THRESHOLD_DEFAULT",
    "HIGH_MEMORY_THRESHOLD_DEFAULT",
    "HIGH_POD_THRESHOLD_DEFAULT",
    "LIMIT_REQUEST_RATIO_THRESHOLD_DEFAULT",
    "HIGH_POD_PERCENTAGE_THRESHOLD_DEFAULT",
    "OPTIMIZER_ANALYSIS_SOURCE_DEFAULT",
    "VERIFY_FIXES_WITH_RENDER_DEFAULT",
    "HELM_TEMPLATE_TIMEOUT_SECONDS_DEFAULT",
    "AI_FIX_LLM_PROVIDER_DEFAULT",
    "AI_FIX_CODEX_MODEL_DEFAULT",
    "AI_FIX_CLAUDE_MODEL_DEFAULT",
    "AI_FIX_FULL_FIX_SYSTEM_PROMPT_DEFAULT",
    "AI_FIX_BULK_PARALLELISM_DEFAULT",
    "EXTREME_RATIOS_THRESHOLD_DEFAULT",
]
