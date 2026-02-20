"""Parsing utilities for TUI screenshot capture."""

from __future__ import annotations

from loguru import logger

from tui_screenshot_capture.constants import DEFAULT_DELAYS, MIN_COLS, MIN_ROWS


def parse_size_safe(size_str: str) -> tuple[int, int] | None:
    """Parse size string like '160x50' into (columns, rows).

    Args:
        size_str: Size string in format 'COLSxROWS'.

    Returns:
        tuple of (columns, rows), or None on error.

    """
    try:
        cols, rows = size_str.lower().split("x")
        cols_int = int(cols)
        rows_int = int(rows)
    except (ValueError, AttributeError, TypeError) as e:
        logger.debug(f"Failed to parse size string '{size_str}': {e}")
        return None

    if cols_int < MIN_COLS:
        return None

    if rows_int < MIN_ROWS:
        return None

    return cols_int, rows_int


def parse_delays_safe(delays_str: str | None) -> list[float]:
    """Parse delays string like '30,60,90' into list of floats.

    Args:
        delays_str: Comma-separated delay values in seconds.

    Returns:
        List of delay values, or DEFAULT_DELAYS if empty/invalid.

    """
    if not delays_str:
        return DEFAULT_DELAYS

    try:
        delays = [
            float(d.strip()) for d in delays_str.split(",")
            if float(d.strip()) > 0
        ]
        if not delays:
            return DEFAULT_DELAYS
        return sorted(set(delays))
    except (ValueError, AttributeError, TypeError):
        return DEFAULT_DELAYS
