"""App-level keyboard bindings.

This module contains Textual Binding objects for app-level bindings
that work from any screen.
"""

from textual.binding import Binding

# ============================================================================
# Textual Binding objects for app-level bindings
# ============================================================================

APP_BINDINGS: list[Binding] = [
    Binding("escape", "back", "Back", priority=True),
    Binding("h", "nav_home", "Summary"),
    Binding("c", "nav_cluster", "Cluster"),
    Binding("C", "nav_charts", "Charts"),
    Binding("e", "nav_export", "Export"),
    Binding("ctrl+s", "nav_settings", "Settings"),
    Binding("R", "nav_recommendations", "Viol+Recs"),
    Binding("?", "show_help", "Help"),
    Binding("r", "refresh", "Refresh"),
    Binding("q", "app.quit", "Quit", priority=True),
]

# Keep tuple-based binding groups for compatibility with tooling and docs.
GLOBAL_BINDINGS: list[tuple[str, str, str]] = [
    (binding.key, binding.action, binding.description) for binding in APP_BINDINGS
]
NAV_BINDINGS: list[tuple[str, str, str]] = [("escape", "back", "Back")]
HELP_BINDINGS: list[tuple[str, str, str]] = [("?", "show_help", "Help")]
REFRESH_BINDINGS: list[tuple[str, str, str]] = [("r", "refresh", "Refresh")]

__all__ = [
    "GLOBAL_BINDINGS",
    "NAV_BINDINGS",
    "HELP_BINDINGS",
    "REFRESH_BINDINGS",
    "APP_BINDINGS",
]
