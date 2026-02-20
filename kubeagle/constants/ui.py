"""UI-related constants (enums, screen configurations).

This module re-exports UI-related constants from the new constants module
for backward compatibility.
"""

from kubeagle.constants import (
    DARK_THEME,
    DEFAULT_THEME,
    INSIDERONE_DARK_THEME,
    LIGHT_THEME,
)
from kubeagle.constants.enums import (
    AppState,
    FetchSources,
    FetchState,
    LoadingState,
    NodeStatus,
    QoSClass,
    Severity,
    ThemeMode,
)

__all__ = [
    "AppState",
    "CATEGORIES",
    "DARK_THEME",
    "DEFAULT_THEME",
    "FetchSources",
    "FetchState",
    "LIGHT_THEME",
    "INSIDERONE_DARK_THEME",
    "LoadingState",
    "NodeStatus",
    "QoSClass",
    "SEVERITIES",
    "Severity",
    "ThemeMode",
]

# Optimizer screen constants (kept here for compatibility)
CATEGORIES = ["resources", "probes", "availability", "security"]
SEVERITIES = ["error", "warning", "info"]
