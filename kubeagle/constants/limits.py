"""Limit and threshold constants for the TUI.

All limit values, thresholds, and validation ranges.
"""

from typing import Final

# ============================================================================
# Pagination
# ============================================================================

DEFAULT_PAGE_SIZE: Final = 50
MAX_PAGE_SIZE: Final = 100
MIN_PAGE_SIZE: Final = 10

# ============================================================================
# Display limits
# ============================================================================

MAX_ROWS_DISPLAY: Final = 1000
MAX_COLUMNS_DISPLAY: Final = 20
MAX_FILTER_DEPTH: Final = 5
MAX_EVENTS_DISPLAY: Final = 100

# ============================================================================
# Health thresholds
# ============================================================================

HEALTHY_THRESHOLD: Final = 90
DEGRADED_THRESHOLD: Final = 70

# ============================================================================
# Resource thresholds (for highlighting in tables)
# ============================================================================

HIGH_CPU_PERCENT: Final = 90
HIGH_MEMORY_PERCENT: Final = 90
WARNING_CPU_PERCENT: Final = 70
WARNING_MEMORY_PERCENT: Final = 70

# ============================================================================
# Validation limits
# ============================================================================

REFRESH_INTERVAL_MIN: Final = 5
THRESHOLD_MIN: Final = 1
THRESHOLD_MAX: Final = 100
AI_FIX_BULK_PARALLELISM_MIN: Final = 1
AI_FIX_BULK_PARALLELISM_MAX: Final = 8

# ============================================================================
# Controller limits
# ============================================================================

MAX_WORKERS: Final = 8

# ============================================================================
# Events limits
# ============================================================================

EVENTS_LIMIT: Final = 100

__all__ = [
    "DEFAULT_PAGE_SIZE",
    "MAX_PAGE_SIZE",
    "MIN_PAGE_SIZE",
    "MAX_ROWS_DISPLAY",
    "MAX_COLUMNS_DISPLAY",
    "MAX_FILTER_DEPTH",
    "MAX_EVENTS_DISPLAY",
    "HEALTHY_THRESHOLD",
    "DEGRADED_THRESHOLD",
    "HIGH_CPU_PERCENT",
    "HIGH_MEMORY_PERCENT",
    "WARNING_CPU_PERCENT",
    "WARNING_MEMORY_PERCENT",
    "REFRESH_INTERVAL_MIN",
    "THRESHOLD_MIN",
    "THRESHOLD_MAX",
    "AI_FIX_BULK_PARALLELISM_MIN",
    "AI_FIX_BULK_PARALLELISM_MAX",
    "MAX_WORKERS",
    "EVENTS_LIMIT",
]
