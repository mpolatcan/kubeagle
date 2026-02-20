"""Custom exceptions for TUI screenshot capture."""

from __future__ import annotations

__all__ = ["TuiCaptureError"]


class TuiCaptureError(Exception):
    """Base exception for TUI screenshot capture errors.

    Raised when screenshot capture operations fail, including widget discovery,
    screenshot generation, PNG conversion, and app initialization failures.
    """
