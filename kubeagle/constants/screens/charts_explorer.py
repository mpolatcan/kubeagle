"""Charts Explorer screen constants."""

from typing import Final

# ============================================================================
# Screen title
# ============================================================================

CHARTS_EXPLORER_TITLE: Final = "Charts Explorer"

# ============================================================================
# Search and filter
# ============================================================================

SEARCH_PLACEHOLDER: Final = "Search charts..."

# ============================================================================
# Button labels
# ============================================================================

BUTTON_FILTER: Final = "Filters"
BUTTON_SEARCH: Final = "Search"
BUTTON_CLEAR: Final = "Clear"
BUTTON_MODE_LOCAL: Final = "Mode: Local"
BUTTON_MODE_CLUSTER: Final = "Mode: Cluster"
BUTTON_ACTIVE_OFF: Final = "Active: Off"
BUTTON_ACTIVE_ON: Final = "Active: On"
BUTTON_COLUMNS: Final = "Columns"

# ============================================================================
# Thresholds
# ============================================================================

EXTREME_RATIOS_THRESHOLD: Final = 2.0

# ============================================================================
# Mode indicator
# ============================================================================

MODE_LOCAL: Final = "LOCAL MODE"
MODE_CLUSTER: Final = "CLUSTER MODE"
STATUS_LOCAL_FILES: Final = "Local files"
STATUS_LIVE_HELM: Final = "Live Helm values"

__all__ = [
    "CHARTS_EXPLORER_TITLE",
    "SEARCH_PLACEHOLDER",
    "BUTTON_FILTER",
    "BUTTON_SEARCH",
    "BUTTON_CLEAR",
    "BUTTON_MODE_LOCAL",
    "BUTTON_MODE_CLUSTER",
    "BUTTON_ACTIVE_OFF",
    "BUTTON_ACTIVE_ON",
    "BUTTON_COLUMNS",
    "EXTREME_RATIOS_THRESHOLD",
    "MODE_LOCAL",
    "MODE_CLUSTER",
    "STATUS_LOCAL_FILES",
    "STATUS_LIVE_HELM",
]
