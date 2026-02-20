"""List command for discovering elements for a specific screen.

Provides the `list-elements` command for inspecting the TUI structure.
Shows tabs, focus targets, toggles, inner tabs, collapsibles, and scrollable widgets.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from kubeagle.app import EKSHelmReporterApp
from loguru import logger

from tui_screenshot_capture.constants import DEFAULT_TERMINAL_SIZE, NAVIGATION_DELAY, get_canonical_name
from tui_screenshot_capture.discovery import (
    discover_collapsibles,
    discover_focus_targets,
    discover_keyboard_tabs,
    discover_screens,
    discover_scrollable_widgets,
    discover_tabbed_content,
    discover_toggles,
)


def register(app: typer.Typer) -> None:
    """Register list command."""

    @app.command()
    def list_elements(
        screen: Annotated[
            str,
            typer.Argument(
                help="Screen name to inspect",
                autocompletion=lambda: list(discover_screens().keys()),
            ),
        ],
        charts_path: Annotated[
            Path | None,
            typer.Option(
                "--charts-path",
                help="Path to Helm charts repository",
            ),
        ] = None,
    ) -> None:
        """List all discoverable elements for a screen.

        Shows tabs, focus targets, toggles, inner tabs, collapsibles, and scrollables.

        Example:
            capture-tui list-elements charts --charts-path ../web-helm-repository

        """
        logger.info(f"Discovering elements for screen: {screen}")

        # Static discovery (from bindings)
        logger.info("    --- TABS (from keyboard bindings) ---")
        tabs = discover_keyboard_tabs(screen)
        if tabs:
            for tab_entry in tabs:
                key = tab_entry.get('key', '?')
                name = tab_entry.get('name', '?')
                desc = tab_entry.get('description', '')
                logger.info(f"    [{key}] {name}: {desc}")
        else:
            logger.info("    (none)")

        logger.info("    --- FOCUS TARGETS (from keyboard bindings) ---")
        focus_targets = discover_focus_targets(screen)
        if focus_targets:
            for target in focus_targets:
                key = target.get('key', '?')
                tgt = target.get('target', '?')
                desc = target.get('description', '')
                logger.info(f"    [{key}] {tgt}: {desc}")
        else:
            logger.info("    (none)")

        logger.info("    --- TOGGLES (from keyboard bindings) ---")
        toggles = discover_toggles(screen)
        if toggles:
            for toggle in toggles:
                key = toggle.get('key', '?')
                name = toggle.get('name', '?')
                desc = toggle.get('description', '')
                logger.info(f"    [{key}] {name}: {desc}")
        else:
            logger.info("    (none)")

        # Dynamic discovery (requires running app)
        async def discover_dynamic() -> None:
            """Run dynamic discovery requiring a running app instance."""
            tui_app = EKSHelmReporterApp(charts_path=charts_path)
            screens = discover_screens()  # Get nav keys for navigation
            nav_screen = get_canonical_name(screen)

            async with tui_app.run_test(size=DEFAULT_TERMINAL_SIZE) as pilot:
                # Navigate to target screen
                if nav_screen != "home" and nav_screen in screens:
                    await pilot.press(screens[nav_screen])
                    await asyncio.sleep(NAVIGATION_DELAY)

                logger.info("    --- INNER TABS (TabbedContent widgets) ---")
                inner_tabs = discover_tabbed_content(tui_app)
                if inner_tabs:
                    for widget in inner_tabs:
                        logger.info(f"    Widget: {widget.get('widget_id', '?')}")
                        for tab in widget.get("tabs", []):
                            logger.info(f"      - {tab.get('id', '?')}: {tab.get('label', 'N/A')}")
                else:
                    logger.info("    (none)")

                logger.info("    --- COLLAPSIBLES ---")
                collapsibles = discover_collapsibles(tui_app)
                if collapsibles:
                    for col in collapsibles:
                        state = "collapsed" if col.get("collapsed", False) else "expanded"
                        logger.info(
                            f"    {col.get('id', '?')}: {col.get('title', '')} ({state})"
                        )
                else:
                    logger.info("    (none)")

                logger.info("    --- SCROLLABLE WIDGETS ---")
                scrollables = list(discover_scrollable_widgets(tui_app))
                if scrollables:
                    for widget in scrollables:
                        scroll_dirs = (
                            ["horizontal"] if widget.get("scroll_x") else []
                        ) + (
                            ["vertical"] if widget.get("scroll_y") else []
                        )
                        logger.info(
                            f"    {widget.get('id', '?')} ({widget.get('type', '?')}): "
                            f"{', '.join(scroll_dirs)}"
                        )
                else:
                    logger.info("    (none)")

        asyncio.run(discover_dynamic())
