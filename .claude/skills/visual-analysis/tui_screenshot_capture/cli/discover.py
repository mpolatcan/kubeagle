"""Discover command for TUI element discovery.

Provides the `discover` command to list all available screens and their
interactive elements (tabs, toggles, focus targets) without capturing.
Supports both static discovery (from bindings) and live discovery (from
running app instance with actual widget detection).
"""

from __future__ import annotations

import asyncio
from itertools import islice
from pathlib import Path
from typing import Annotated

import typer
from kubeagle.app import EKSHelmReporterApp
from loguru import logger

from tui_screenshot_capture.constants import DEFAULT_SCREEN_LIMIT, DEFAULT_TERMINAL_SIZE, get_canonical_name
from tui_screenshot_capture.discovery import (
    DiscoveryResult,
    analyze_screen_live,
    build_discovery_result,
    discover_screens,
)


async def _run_live_discover(
    discovery_result: DiscoveryResult,
    charts_path: Path | None,
    screen_limit: int,
    initial_delay: float = 2.0,
) -> None:
    """Run live discovery to analyze screens with running TUI.

    Args:
        discovery_result: The discovery result containing screen states.
        charts_path: Optional path to Helm charts repository.
        screen_limit: Maximum number of screens to analyze (default: 3).
        initial_delay: Wait time after navigating to screen.

    """
    tui_app = EKSHelmReporterApp(charts_path=charts_path)
    nav_key_map = discover_screens()  # Map of screen_name -> nav_key

    async with tui_app.run_test(size=DEFAULT_TERMINAL_SIZE) as pilot:
        # Process only the requested number of screens efficiently
        for screen_name in islice(discovery_result.screens.keys(), screen_limit):
            nav_screen = get_canonical_name(screen_name)
            nav_key = nav_key_map.get(nav_screen, "h")

            # Navigate to the target screen
            if nav_screen != "home" and nav_screen in nav_key_map:
                await pilot.press(nav_key_map[nav_screen])
            elif nav_screen != "home":
                logger.warning(f"No navigation key for '{nav_screen}'")
                continue

            await asyncio.sleep(initial_delay)

            state = analyze_screen_live(tui_app, screen_name, nav_key)

            logger.info(f"  [{screen_name}] LIVE STATE:")
            logger.info(f"    Scrollables: {len(state.scrollables)}")
            for s in state.scrollables:
                v_icon = "↕" if s.has_vertical else " "
                h_icon = "↔" if s.has_horizontal else " "
                logger.info(f"      - {s.widget_id} ({s.widget_type}) {v_icon}{h_icon}")
                if s.has_vertical:
                    logger.info(
                        f"        Vertical: {s.max_scroll_y}px, "
                        f"positions: {s.scroll_positions_v}"
                    )
                if s.has_horizontal:
                    logger.info(
                        f"        Horizontal: {s.max_scroll_x}px, "
                        f"positions: {s.scroll_positions_h}"
                    )

            logger.info(f"    Inner tabs: {len(state.inner_tabs)}")
            logger.info(f"    Collapsibles: {len(state.collapsibles)}")
            logger.info("")


def register(app: typer.Typer) -> None:
    """Register discover command."""

    @app.command()
    def discover(  # noqa: ARG001 - used by typer
        list_screens: Annotated[
            bool,
            typer.Option(
                "--list-screens",
                help="List all available screens with their navigation keys",
            ),
        ] = False,
        charts_path: Annotated[
            Path | None,
            typer.Option(
                "--charts-path",
                help="Path to Helm charts repository",
            ),
        ] = None,
        live: Annotated[
            bool,
            typer.Option(
                "--live",
                help="Run live discovery (requires app to be running)",
            ),
        ] = False,
        screen_limit: Annotated[
            int,
            typer.Option(
                "--screen-limit",
                help=f"Maximum screens to analyze in live discovery (default: {DEFAULT_SCREEN_LIMIT})",
            ),
        ] = DEFAULT_SCREEN_LIMIT,
        initial_delay: Annotated[
            float,
            typer.Option(
                "--initial-delay",
                help="Wait time after navigating to screen (seconds)",
            ),
        ] = 2.0,
    ) -> None:
        """Discover all screens and their elements without capturing.

        Shows what would be captured by the capture command.

        Examples:
            # List all screens with navigation keys
            capture-tui discover --list-screens

            # Quick discovery from bindings only
            capture-tui discover

            # Live discovery with actual scrollbar detection
            capture-tui discover --live --charts-path ../web-helm-repository

        """
        # Handle --list-screens (quick listing of screens only)
        if list_screens:
            screens = discover_screens()
            logger.info("Available screens:")
            for name, key in sorted(screens.items()):
                logger.info(f"  {name}: key='{key}'")
            return

        logger.info("=== TUI Discovery ===")

        result = build_discovery_result()

        logger.info(f"Total screens: {result.total_screens}")

        for name, state in result.screens.items():
            logger.info(f"  [{name}] nav_key='{state.nav_key}'")

            if state.keyboard_tabs:
                logger.info(f"    Keyboard tabs: {len(state.keyboard_tabs)}")
                for tab in state.keyboard_tabs:
                    key = tab.tab_key if tab.tab_key is not None else "?"
                    logger.info(f"      - [{key}] {tab.tab_name}")

            if state.toggles:
                logger.info(f"    Toggles: {len(state.toggles)}")
                for toggle in state.toggles:
                    logger.info(f"      - [{toggle.get('key', '?')}] {toggle.get('name', '?')}")

            if state.focus_targets:
                logger.info(f"    Focus targets: {len(state.focus_targets)}")
                for focus in state.focus_targets:
                    logger.info(f"      - [{focus.get('key', '?')}] {focus.get('target', '?')}")

            logger.info("")

        if live:
            logger.info("Running live discovery...")
            asyncio.run(
                _run_live_discover(
                    result,
                    charts_path,
                    screen_limit=screen_limit,
                    initial_delay=initial_delay,
                )
            )
