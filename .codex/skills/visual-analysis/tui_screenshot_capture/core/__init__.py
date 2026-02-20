"""Capture configuration and exceptions for TUI screenshot capture."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from tui_screenshot_capture.constants import DEFAULT_DELAYS, DEFAULT_OUTPUT_DIR, DEFAULT_TERMINAL_SIZE, FALLBACK_DELAY
from tui_screenshot_capture.core.exceptions import TuiCaptureError


@dataclass(slots=True)
class CaptureConfig:
    """Configuration for capture engine."""

    output_dir: Path = field(default_factory=lambda: Path(DEFAULT_OUTPUT_DIR))
    size: tuple[int, int] = DEFAULT_TERMINAL_SIZE
    png_scale: float = 1.0
    keep_svg: bool = False
    charts_path: Path | None = None
    delays: list[float] = field(default_factory=lambda: DEFAULT_DELAYS)  # Multi-delay capture for freeze detection
    scroll_delay: float = 0.3  # Wait between scroll positions
    tab_delay: float = 0.5  # Wait after tab switch
    # scroll_positions exclude 0% (already captured as base screenshot)
    # Positions are: 20%, 40%, 60%, 80%, 100% (5 steps total, see DEFAULT_SCROLL_STEPS)
    # Global timeout for entire capture operation (seconds)
    # Use 0 for no timeout, positive value to prevent hangs
    capture_timeout: float = 0.0  # Default: no timeout (0 means unlimited)

    def __post_init__(self) -> None:
        """Validate and sort delays."""
        if not self.delays:
            self.delays = FALLBACK_DELAY
        else:
            # Ensure delays are sorted and unique
            self.delays = sorted(set(self.delays))


@dataclass(slots=True)
class CaptureResult:
    """Result of a capture operation."""

    success: bool
    file_path: Path | None = None
    error: str | None = None


__all__ = [
    "CaptureConfig",
    "CaptureResult",
    "TuiCaptureError",
]
