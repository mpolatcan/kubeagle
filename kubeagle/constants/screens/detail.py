"""Detail screen constants (Optimizer, Recommendations, Chart Detail)."""

from typing import Final

# ============================================================================
# Optimizer categories and severities
# ============================================================================

OPTIMIZER_CATEGORIES: list[str] = ["resources", "probes", "availability", "security"]
OPTIMIZER_SEVERITIES: list[str] = ["error", "warning", "info"]

# ============================================================================
# Button labels
# ============================================================================

BUTTON_APPLY_ALL: Final = "Apply All"
BUTTON_FIX: Final = "Fix"
BUTTON_PREVIEW: Final = "Preview"

# ============================================================================
# Filter labels
# ============================================================================

FILTER_CATEGORY: Final = "Category"
FILTER_SEVERITY: Final = "Severity"

__all__ = [
    "OPTIMIZER_CATEGORIES",
    "OPTIMIZER_SEVERITIES",
    "BUTTON_APPLY_ALL",
    "BUTTON_FIX",
    "BUTTON_PREVIEW",
    "FILTER_CATEGORY",
    "FILTER_SEVERITY",
]
