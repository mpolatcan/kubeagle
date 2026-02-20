"""Timeout constants for the TUI.

All timeout and interval values for API requests, async operations, and refresh cycles.
"""

from typing import Final

# ============================================================================
# API/Cluster timeouts (string format for kubectl)
# ============================================================================

CLUSTER_REQUEST_TIMEOUT: Final = "30s"

# Process-level command timeouts (must be greater than request timeout)
KUBECTL_COMMAND_TIMEOUT: Final = 45
HELM_COMMAND_TIMEOUT: Final = 30

# ============================================================================
# General timeouts (float, in seconds)
# ============================================================================

DEFAULT_TIMEOUT: Final = 30.0
LONG_TIMEOUT: Final = 60.0
SHORT_TIMEOUT: Final = 10.0

# ============================================================================
# Async operation timeouts (float, in seconds)
# ============================================================================

CLUSTER_CHECK_TIMEOUT: Final = 12.0
NODE_FETCH_TIMEOUT: Final = 50.0
NODE_GROUPS_TIMEOUT: Final = 50.0
VIOLATION_CHECK_TIMEOUT: Final = 60.0
CHART_ANALYSIS_TIMEOUT: Final = 180.0

# ============================================================================
# Refresh intervals (float, in seconds)
# ============================================================================

STATUS_UPDATE_INTERVAL: Final = 30.0

__all__ = [
    "CLUSTER_REQUEST_TIMEOUT",
    "KUBECTL_COMMAND_TIMEOUT",
    "HELM_COMMAND_TIMEOUT",
    "DEFAULT_TIMEOUT",
    "LONG_TIMEOUT",
    "SHORT_TIMEOUT",
    "CLUSTER_CHECK_TIMEOUT",
    "NODE_FETCH_TIMEOUT",
    "NODE_GROUPS_TIMEOUT",
    "VIOLATION_CHECK_TIMEOUT",
    "CHART_ANALYSIS_TIMEOUT",
    "STATUS_UPDATE_INTERVAL",
]
