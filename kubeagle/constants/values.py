"""Scalar constants for the TUI.

All application-level constants with proper type hints using Final.
"""

from typing import Final

# ============================================================================
# Application
# ============================================================================

APP_TITLE: Final = "KubEagle"

# ============================================================================
# Colors (hex strings for Theme compatibility)
# ============================================================================

COLOR_PRIMARY: Final = "#007ACC"  # Blue
COLOR_SECONDARY: Final = "#6C757D"  # Gray
COLOR_ACCENT: Final = "#17A2B8"  # Teal
COLOR_SUCCESS: Final = "#28A745"  # Green
COLOR_WARNING: Final = "#FFC107"  # Yellow
COLOR_ERROR: Final = "#DC3545"  # Red

# ============================================================================
# Layout
# ============================================================================

SPACING: Final = 1

# ============================================================================
# Data
# ============================================================================

TABLE_PAGE_SIZE: Final = 50

# ============================================================================
# Caching
# ============================================================================

MAX_CACHE_AGE_SECONDS: Final = 300  # 5 minutes

# ============================================================================
# Status strings
# ============================================================================

STATUS_DISCONNECTED: Final = "Disconnected"
STATUS_CONNECTED: Final = "Connected"
STATUS_LOADING: Final = "Loading..."

# ============================================================================
# Health status (markup for rich text display)
# ============================================================================

HEALTHY: Final = "[green]HEALTHY[/green]"
DEGRADED: Final = "[yellow]DEGRADED[/yellow]"
UNHEALTHY: Final = "[red]UNHEALTHY[/red]"

# ============================================================================
# Settings screen placeholders
# ============================================================================

PLACEHOLDER_CHARTS_PATH: Final = "/path/to/helm/charts"
PLACEHOLDER_ACTIVE_CHARTS: Final = "active-charts.txt (optional)"
PLACEHOLDER_CODEOWNERS: Final = "CODEOWNERS (optional)"
PLACEHOLDER_REFRESH_INTERVAL: Final = "30"
PLACEHOLDER_EXPORT_PATH: Final = "./reports"
PLACEHOLDER_EVENT_AGE: Final = "1.0"
PLACEHOLDER_THRESHOLD: Final = "80"
PLACEHOLDER_LIMIT_REQUEST: Final = "3.0"
PLACEHOLDER_AI_FIX_BULK_PARALLELISM: Final = "2"

# ============================================================================
# Error and status messages
# ============================================================================

MSG_CLUSTER_CONNECTION_FAILED: Final = "Cluster connection failed or timed out"
MSG_CLUSTER_ERROR: Final = "Cluster error: {str(e)}"
MSG_OPERATION_CANCELLED: Final = "Operation cancelled"
MSG_INITIALIZING: Final = "Initializing..."
MSG_LOADING: Final = "Loading..."
MSG_CLUSTER_NAME_DEFAULT: Final = "EKS Cluster"
MSG_UNKNOWN: Final = "Unknown"
MSG_NEVER: Final = "Never"

__all__ = [
    "APP_TITLE",
    "COLOR_PRIMARY",
    "COLOR_SECONDARY",
    "COLOR_ACCENT",
    "COLOR_SUCCESS",
    "COLOR_WARNING",
    "COLOR_ERROR",
    "SPACING",
    "TABLE_PAGE_SIZE",
    "MAX_CACHE_AGE_SECONDS",
    "STATUS_DISCONNECTED",
    "STATUS_CONNECTED",
    "STATUS_LOADING",
    "HEALTHY",
    "DEGRADED",
    "UNHEALTHY",
    "PLACEHOLDER_CHARTS_PATH",
    "PLACEHOLDER_ACTIVE_CHARTS",
    "PLACEHOLDER_CODEOWNERS",
    "PLACEHOLDER_REFRESH_INTERVAL",
    "PLACEHOLDER_EXPORT_PATH",
    "PLACEHOLDER_EVENT_AGE",
    "PLACEHOLDER_THRESHOLD",
    "PLACEHOLDER_LIMIT_REQUEST",
    "PLACEHOLDER_AI_FIX_BULK_PARALLELISM",
    "MSG_CLUSTER_CONNECTION_FAILED",
    "MSG_CLUSTER_ERROR",
    "MSG_OPERATION_CANCELLED",
    "MSG_INITIALIZING",
    "MSG_LOADING",
    "MSG_CLUSTER_NAME_DEFAULT",
    "MSG_UNKNOWN",
    "MSG_NEVER",
]
