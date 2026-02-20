"""Package entry point for capture-tui CLI.

Allows running the TUI Screenshot Capture tool directly with:
    python -m tui_screenshot_capture

This module creates the CLI app and executes it when run as a module.
"""

from __future__ import annotations

from tui_screenshot_capture.cli import create_app

if __name__ == "__main__":
    app = create_app()
    app()
