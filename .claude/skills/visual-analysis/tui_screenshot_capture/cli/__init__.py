"""CLI subpackage for TUI screenshot capture."""

from __future__ import annotations

import sys
from functools import lru_cache
from typing import Annotated

import typer
from loguru import logger

# Register all command modules at module level
from tui_screenshot_capture.cli import capture, discover, prompt
from tui_screenshot_capture.cli import list as list_cmd
from tui_screenshot_capture.constants import VERSION

# Remove default handler and configure logging
logger.remove()
logger.add(
    sys.stderr,
    format="<level>{message}</level>",
    level="INFO",
)

__all__ = ["app", "create_app"]


@lru_cache(maxsize=1)
def create_app() -> typer.Typer:
    """Create and configure the Typer CLI application.

    Cached to avoid repeated creation on module-level access.

    Returns:
        Configured Typer application with all commands registered.
    """
    app = typer.Typer(
        name="capture-tui",
        help="Capture TUI screenshots with proper multi-delay and resolution support.",
        add_completion=False,
    )

    capture.register(app)
    discover.register(app)
    list_cmd.register(app)
    prompt.register(app)

    # Add callback
    @app.callback()
    def main(  # noqa: ARG001 - used by typer
        *,  # Force keyword-only to avoid FBT002 warning
        version: Annotated[
            bool,
            typer.Option("--version", help="Show version and exit"),
        ] = False,
    ) -> None:
        """TUI Screenshot Capture Utility.

        This utility solves two critical problems with Textual screenshot capture:

        1. Multiple delays in single run: Each `textual run --screenshot N` starts
           a fresh app instance. This utility captures multiple delays WITHIN A
           SINGLE APP RUN.

        2. Resolution control: The `textual run` CLI doesn't expose the `size`
           parameter. This utility allows specifying exact terminal size.

        Raises:
            typer.Exit: When --version flag is used.
        """
        if version:
            logger.info(f"capture-tui v{VERSION}")
            raise typer.Exit()

    return app


# Module-level app accessor using lazy initialization via lru_cache
# This allows the app to be used as an entry point while deferring creation
# until it's actually needed (avoids issues with testing and circular imports)
def __getattr__(name: str) -> typer.Typer:
    """Support module-level app access for console_scripts entry point."""
    if name == "app":
        return create_app()
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
