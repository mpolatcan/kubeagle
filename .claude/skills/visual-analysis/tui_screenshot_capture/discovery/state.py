"""Screen state tracking for comprehensive TUI discovery."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CaptureStatus(Enum):
    """Status of capture operation."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PARTIAL = "partial"  # Partially completed (some captures failed)
    FAILED = "failed"


@dataclass(slots=True)
class ScrollState:
    """State of a scrollable widget."""

    widget_id: str
    widget_type: str
    has_vertical: bool = False
    has_horizontal: bool = False
    content_height: int = 0
    content_width: int = 0
    viewport_height: int = 0
    viewport_width: int = 0
    max_scroll_y: int = 0
    max_scroll_x: int = 0
    scroll_positions_v: list[int] = field(default_factory=list)
    scroll_positions_h: list[int] = field(default_factory=list)
    captured_positions_v: list[int] = field(default_factory=list)
    captured_positions_h: list[int] = field(default_factory=list)
    status: CaptureStatus = CaptureStatus.PENDING
    # Track whether widget has explicit ID for cleaner filenames
    has_explicit_id: bool = False
    # Store widget reference directly to avoid lookup failures
    # (especially for Screen widgets which can't be queried by ID)
    widget: Any = None


@dataclass(slots=True)
class TabState:
    """State of a tab (keyboard tab or inner tab)."""

    tab_id: str
    tab_name: str
    tab_key: str | None = None  # Keyboard key to switch to this tab
    tab_index: int = 0
    is_active: bool = False
    scrollables: list[ScrollState] = field(default_factory=list)
    status: CaptureStatus = CaptureStatus.PENDING


@dataclass(slots=True)
class ScreenState:
    """Complete state of a screen for capture tracking."""

    screen_name: str
    nav_key: str  # Keyboard key to navigate to this screen
    is_current: bool = False

    # Direct scrollables on the screen (no tab context)
    scrollables: list[ScrollState] = field(default_factory=list)

    # Keyboard-accessible tabs (switch_tab_* bindings)
    keyboard_tabs: list[TabState] = field(default_factory=list)

    # TabbedContent/ContentSwitcher widgets
    inner_tabs: list[TabState] = field(default_factory=list)

    # Collapsible widgets
    collapsibles: list[dict[str, Any]] = field(default_factory=list)

    # Focus targets
    focus_targets: list[dict[str, str]] = field(default_factory=list)

    # Toggle actions
    toggles: list[dict[str, str]] = field(default_factory=list)

    # Overall status
    status: CaptureStatus = CaptureStatus.PENDING
    error_message: str | None = None

    # Capture statistics
    total_captures: int = 0
    completed_captures: int = 0

    @property
    def progress_percent(self) -> float:
        """Get capture progress as a percentage (0.0 to 100.0)."""
        if self.total_captures == 0:
            return 0.0
        return (self.completed_captures / self.total_captures) * 100


@dataclass(slots=True)
class DiscoveryResult:
    """Complete discovery result for all screens."""

    screens: dict[str, ScreenState] = field(default_factory=dict)
    current_screen: str | None = None
    total_screens: int = 0
    completed_screens: int = 0
    status: CaptureStatus = CaptureStatus.PENDING

    @property
    def progress_percent(self) -> float:
        """Get overall progress as a percentage (0.0 to 100.0)."""
        if self.total_screens == 0:
            return 0.0
        return (self.completed_screens / self.total_screens) * 100

    def add_screen(self, screen: ScreenState) -> None:
        """Add a screen to the result."""
        self.screens[screen.screen_name] = screen
        self.total_screens += 1

    def mark_screen_complete(self, name: str) -> None:
        """Mark a screen as completed.

        Args:
            name: Name of the screen to mark complete.

        """
        if name in self.screens:
            self.screens[name].status = CaptureStatus.COMPLETED
            self.completed_screens += 1

    def to_summary(self) -> dict[str, Any]:
        """Generate a summary of the discovery result.

        Returns:
            Dictionary with progress statistics and screen details.
        """
        return {
            "total_screens": self.total_screens,
            "completed_screens": self.completed_screens,
            "progress": f"{self.progress_percent:.1f}%",
            "status": self.status.value,
            "screens": {
                name: {
                    "status": state.status.value,
                    "has_scrollbars": bool(state.scrollables),
                    "has_tabs": bool(state.keyboard_tabs),
                    "has_inner_tabs": bool(state.inner_tabs),
                    "scrollables_count": len(state.scrollables),
                    "keyboard_tabs_count": len(state.keyboard_tabs),
                    "inner_tabs_count": len(state.inner_tabs),
                    "progress": f"{state.progress_percent:.1f}%",
                }
                for name, state in self.screens.items()
            },
        }
