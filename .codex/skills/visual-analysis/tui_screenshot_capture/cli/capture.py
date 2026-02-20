"""Single screen, multiple screens, or all screens capture command.

Provides the `capture` command for capturing screenshots of TUI screens.
With --all flag, captures all available screens sequentially.
Without --all flag, captures one or more specified screens.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from pathlib import Path
from typing import Annotated

import typer
from loguru import logger

from tui_screenshot_capture.analysis import generate_analysis_prompt
from tui_screenshot_capture.constants import (
    CAPTURED_EXTENSIONS,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_PNG_SCALE,
    DEFAULT_TERMINAL_SIZE_STR,
)
from tui_screenshot_capture.core import CaptureConfig
from tui_screenshot_capture.discovery import ScreenState, discover_screens
from tui_screenshot_capture.engine import CaptureEngine
from tui_screenshot_capture.utils import parse_delays_safe, parse_size_safe


def _get_screen_names_cached() -> tuple[str, ...]:
    """Get screen names for autocompletion.

    Note: discover_screens() already uses @lru_cache internally.

    Returns:
        Tuple of screen names (immutable for Typer autocompletion).
    """
    return tuple(discover_screens().keys())


def _create_config(
    output_dir: Path,
    size: tuple[int, int],
    png_scale: float,
    keep_svg: bool,
    charts_path: Path | None,
    delays: list[float],
    scroll_delay: float,
    tab_delay: float,
    timeout: float | None,
) -> CaptureConfig:
    """Create a CaptureConfig with common parameters.

    Args:
        output_dir: Directory to save screenshots.
        size: Terminal size as (columns, rows).
        png_scale: PNG scaling factor.
        keep_svg: If False, delete SVG after PNG conversion.
        charts_path: Optional path to Helm charts repository.
        delays: List of delays in seconds for multi-delay capture.
        scroll_delay: Wait time between scroll positions.
        tab_delay: Wait time after switching tabs.
        timeout: Optional global timeout in seconds.

    Returns:
        Configured CaptureConfig instance.

    """
    return CaptureConfig(
        output_dir=output_dir,
        size=size,
        png_scale=png_scale,
        keep_svg=keep_svg,
        charts_path=charts_path,
        delays=delays,
        scroll_delay=scroll_delay,
        tab_delay=tab_delay,
        capture_timeout=timeout if timeout is not None else 0.0,
    )


def _setup_progress_callbacks(engine: CaptureEngine) -> None:
    """Set up standard progress callbacks on a CaptureEngine.

    Args:
        engine: The CaptureEngine to configure.

    """
    def on_screen_start(screen_name: str) -> None:
        logger.info(f"Capturing {screen_name} screen...")

    def on_screen_complete(screen_name: str, state: ScreenState) -> None:
        status_icon = "\u2713" if state.status.value == "completed" else "\u2717"
        logger.info(f"  [{status_icon}] {screen_name} ({state.completed_captures} captures)")

    engine.on_screen_start = on_screen_start
    engine.on_screen_complete = on_screen_complete


def _build_results_dict(
    screen_names: Iterable[str],
    output_dir: Path,
) -> dict[str, list[Path]]:
    """Build results dict by scanning output directories for captured files.

    Args:
        screen_names: Screen names to scan (list, dict keys, or any iterable).
        output_dir: Base output directory.

    Returns:
        Dict mapping screen names to lists of captured file paths.

    """
    results: dict[str, list[Path]] = {}
    for screen_name in screen_names:
        screen_dir = output_dir / screen_name
        if screen_dir.exists():
            results[screen_name] = [
                f for f in screen_dir.iterdir()
                if f.suffix[1:].lower() in CAPTURED_EXTENSIONS
            ]
        else:
            results[screen_name] = []
    return results


def register(app: typer.Typer) -> None:
    """Register capture command (single screen or all screens)."""

    @app.command()
    def capture(
        screens: Annotated[
            list[str] | None,
            typer.Argument(
                help="Screen name(s) to capture (one or more, required unless --all is specified)",
                autocompletion=lambda: list(_get_screen_names_cached()),
            ),
        ] = None,
        all_screens: Annotated[
            bool,
            typer.Option(
                "--all",
                "-a",
                help="Capture all available screens (use instead of specifying screen names)",
            ),
        ] = False,
        tab: Annotated[
            str | None,
            typer.Option(
                "--tab",
                "-t",
                help="Tab index to capture (e.g., '1', '2', 'all')",
            ),
        ] = None,
        all_tabs: Annotated[
            bool,
            typer.Option(
                "--all-tabs",
                help="Capture all tabs of the specified screen",
            ),
        ] = False,
        skip_tabs: Annotated[
            bool,
            typer.Option(
                "--skip-tabs",
                help="Skip automatic tab discovery and capture",
            ),
        ] = False,
        output: Annotated[
            Path,
            typer.Option(
                "--output",
                "-o",
                help="Output directory for screenshots",
            ),
        ] = Path(DEFAULT_OUTPUT_DIR),
        session_id: Annotated[
            str | None,
            typer.Option(
                "--id",
                help="Session identifier (e.g., 'PRD-001-feature', 'fix-01'). Screenshots go to {output}/{id}/{screen}/",
            ),
        ] = None,
        size: Annotated[
            str,
            typer.Option(
                "--size",
                "-s",
                help=f"Terminal size as COLSxROWS (default: {DEFAULT_TERMINAL_SIZE_STR})",
            ),
        ] = DEFAULT_TERMINAL_SIZE_STR,
        png_scale: Annotated[
            float,
            typer.Option(
                "--png-scale",
                help=f"PNG scale factor (default: {DEFAULT_PNG_SCALE})",
            ),
        ] = DEFAULT_PNG_SCALE,
        charts_path: Annotated[
            Path | None,
            typer.Option(
                "--charts-path",
                help="Path to Helm charts repository",
            ),
        ] = None,
        keep_svg: Annotated[
            bool,
            typer.Option(
                "--keep-svg",
                help="Keep SVG files after PNG conversion (default: delete SVGs)",
            ),
        ] = False,
        scroll_vertical: Annotated[
            bool | None,
            typer.Option(
                "--scroll-vertical",
                help="Enable vertical scroll capture (default: auto-detect)",
            ),
        ] = None,
        scroll_horizontal: Annotated[
            bool | None,
            typer.Option(
                "--scroll-horizontal",
                help="Enable horizontal scroll capture (default: auto-detect)",
            ),
        ] = None,
        skip_toggles: Annotated[
            bool,
            typer.Option(
                "--skip-toggles",
                help="Skip toggle state capture",
            ),
        ] = False,
        skip_inner_tabs: Annotated[
            bool,
            typer.Option(
                "--skip-inner-tabs",
                help="Skip TabbedContent inner tabs capture",
            ),
        ] = False,
        skip_collapsibles: Annotated[
            bool,
            typer.Option(
                "--skip-collapsibles",
                help="Skip collapsible widget capture",
            ),
        ] = False,
        skip_all_discovery: Annotated[
            bool,
            typer.Option(
                "--skip-all-discovery",
                help="Skip all auto-discovery (tabs, scroll, toggles, inner tabs, collapsibles)",
            ),
        ] = False,
        delays: Annotated[
            str | None,
            typer.Option(
                "--delays",
                "-d",
                help="Comma-separated delays in seconds for multi-delay capture (e.g., '30,60,90'). At each delay, base screenshot is captured. At final delay, scroll/toggles/focus/tabs/collapsibles are also captured.",
            ),
        ] = None,
        scroll_delay: Annotated[
            float,
            typer.Option(
                "--scroll-delay",
                help="Wait time between scroll positions (seconds)",
            ),
        ] = 0.3,
        tab_delay: Annotated[
            float,
            typer.Option(
                "--tab-delay",
                help="Wait time after switching tabs (seconds)",
            ),
        ] = 0.5,
        timeout: Annotated[
            float | None,
            typer.Option(
                "--timeout",
                "-T",
                help="Global timeout for entire capture operation in seconds (0=no timeout, default=0). Prevents hangs.",
            ),
        ] = None,
        analyze: Annotated[
            bool,
            typer.Option(
                "--analyze",
                help="Generate AI analysis prompts for captured screenshots. Use with Claude Code's Read tool for native multimodal vision analysis.",
            ),
        ] = False,
        analysis_type: Annotated[
            str,
            typer.Option(
                "--analysis-type",
                help="Type of analysis: quick, standard, data, freeze, visual, layout, full. (default: full)",
            ),
        ] = "full",
    ) -> None:
        """Capture TUI screenshots.

        Capture one or more screens, or all screens with automatic discovery.
        Use --all to capture all screens, or specify one or more screen names.

        Examples:
            # Capture all screens
            capture-tui capture --all --output /tmp/screenshots

            # Capture a single screen
            capture-tui capture charts --output /tmp/screenshots

            # Capture multiple specific screens (single app instance)
            capture-tui capture home cluster charts --output /tmp/screenshots

            # Capture specific tab
            capture-tui capture charts --tab 2 --output /tmp/screenshots

            # Capture all tabs of a screen
            capture-tui capture charts --all-tabs --output /tmp/screenshots

            # Skip tab discovery
            capture-tui capture charts --skip-tabs --output /tmp/screenshots

            # Auto-detect and capture scroll positions
            capture-tui capture optimizer --output /tmp/screenshots

            # Disable scroll capture
            capture-tui capture optimizer --scroll-vertical=false --scroll-horizontal=false

            # Skip toggle state capture
            capture-tui capture charts --skip-toggles --output /tmp/screenshots

            # Skip all auto-discovery (minimal capture)
            capture-tui capture optimizer --skip-all-discovery --output /tmp/screenshots

            # Capture with custom delays (multi-delay capture)
            capture-tui capture charts --delays 30,60,90 --scroll-delay 0.5 --tab-delay 1.0

        """
        # Validate arguments
        if all_screens and screens:
            logger.error("Cannot specify both screen names and --all flag")
            raise typer.Exit(code=1)

        if not all_screens and not screens:
            logger.error("Must specify at least one screen name or use --all flag")
            raise typer.Exit(code=1)

        # Validate screen names if provided
        if screens:
            available_screens = set(_get_screen_names_cached())
            invalid_screens = [s for s in screens if s not in available_screens]
            if invalid_screens:
                logger.error(f"Invalid screen name(s): {', '.join(invalid_screens)}")
                logger.info(f"Available screens: {', '.join(sorted(available_screens))}")
                raise typer.Exit(code=1)

        parsed_size = parse_size_safe(size)
        if parsed_size is None:
            raise typer.Exit(code=1)

        # Apply PRD-specific output path if provided
        if session_id:
            output = output / session_id

        # Handle --skip-all-discovery flag
        if skip_all_discovery:
            skip_tabs = skip_toggles = skip_inner_tabs = skip_collapsibles = True
            scroll_vertical = scroll_horizontal = False

        # Parse delays
        parsed_delays = parse_delays_safe(delays)
        delays_str = ",".join(str(d) for d in parsed_delays)

        logger.info(f"Terminal size: {parsed_size[0]}x{parsed_size[1]} (columns x rows)")
        logger.info(f"Output: {output}")
        logger.info(f"PNG scale: {png_scale}x")
        logger.info(f"Delays: {delays_str}s (multi-delay: base screenshots at each delay, full capture at final)")
        if timeout is not None:
            logger.info(f"Timeout: {timeout}s (0=no timeout)")
        if charts_path:
            logger.info(f"Charts path: {charts_path}")

        captured_files: list[Path] = []

        if all_screens:
            # Capture all screens
            logger.info("Capturing all screens...")
            try:
                results = asyncio.run(
                    _capture_all_screens_with_engine(
                        output_dir=output,
                        size=parsed_size,
                        png_scale=png_scale,
                        charts_path=charts_path,
                        keep_svg=keep_svg,
                        delays=parsed_delays,
                        scroll_delay=scroll_delay,
                        tab_delay=tab_delay,
                        timeout=timeout,
                    ),
                )
                total_files = sum(len(files) for files in results.values())
                logger.info(f"Captured {total_files} files across {len(results)} screens")
                # Flatten results for analysis
                for files_list in results.values():
                    captured_files.extend(files_list)
            except asyncio.TimeoutError:
                logger.error(f"Capture timed out after {timeout}s for all screens")
                raise typer.Exit(code=1) from None
            except KeyboardInterrupt:
                logger.info("Capture cancelled by user")
                raise typer.Exit(code=130) from None
        elif screens and len(screens) == 1:
            # Capture single screen (with full options support)
            screen = screens[0]
            logger.info(f"Capturing {screen} screen...")
            try:
                files: list[Path] = asyncio.run(
                    _capture_screen_with_engine(
                        screen=screen,
                        output_dir=output,
                        size=parsed_size,
                        png_scale=png_scale,
                        charts_path=charts_path,
                        tab=tab,
                        keep_svg=keep_svg,
                        all_tabs=all_tabs,
                        skip_tabs=skip_tabs,
                        scroll_vertical=scroll_vertical,
                        scroll_horizontal=scroll_horizontal,
                        skip_toggles=skip_toggles,
                        skip_inner_tabs=skip_inner_tabs,
                        skip_collapsibles=skip_collapsibles,
                        delays=parsed_delays,
                        scroll_delay=scroll_delay,
                        tab_delay=tab_delay,
                        timeout=timeout,
                    ),
                )
                logger.info(f"Captured {len(files)} files")
                captured_files = files
            except asyncio.TimeoutError:
                logger.error(f"Capture timed out after {timeout}s for screen '{screen}'")
                raise typer.Exit(code=1) from None
            except KeyboardInterrupt:
                logger.info("Capture cancelled by user")
                raise typer.Exit(code=130) from None
        else:
            # Capture multiple specific screens (single app instance)
            assert screens is not None and len(screens) > 1
            logger.info(f"Capturing {len(screens)} screens: {', '.join(screens)}...")
            try:
                results = asyncio.run(
                    _capture_selected_screens_with_engine(
                        screen_names=screens,
                        output_dir=output,
                        size=parsed_size,
                        png_scale=png_scale,
                        charts_path=charts_path,
                        keep_svg=keep_svg,
                        delays=parsed_delays,
                        scroll_delay=scroll_delay,
                        tab_delay=tab_delay,
                        timeout=timeout,
                    ),
                )
                total_files = sum(len(files) for files in results.values())
                logger.info(f"Captured {total_files} files across {len(results)} screens")
                # Flatten results for analysis
                for files_list in results.values():
                    captured_files.extend(files_list)
            except asyncio.TimeoutError:
                logger.error(f"Capture timed out after {timeout}s for selected screens")
                raise typer.Exit(code=1) from None
            except KeyboardInterrupt:
                logger.info("Capture cancelled by user")
                raise typer.Exit(code=130) from None

        # Generate analysis prompts if requested
        if analyze and captured_files:
            _print_analysis_prompts(captured_files, analysis_type, parsed_delays)


async def _capture_screen_with_engine(
    screen: str,
    output_dir: Path,
    size: tuple[int, int],
    png_scale: float = 1.0,
    charts_path: Path | None = None,
    tab: str | None = None,
    keep_svg: bool = False,
    all_tabs: bool = False,
    skip_tabs: bool = False,
    scroll_vertical: bool | None = None,
    scroll_horizontal: bool | None = None,
    skip_toggles: bool = False,
    skip_inner_tabs: bool = False,
    skip_collapsibles: bool = False,
    *,
    delays: list[float],
    scroll_delay: float = 0.3,
    tab_delay: float = 0.5,
    timeout: float | None = None,
) -> list[Path]:
    """Capture a single screen using CaptureEngine.

    Args:
        screen: Screen name to capture.
        output_dir: Directory to save screenshots.
        size: Terminal size as (columns, rows).
        png_scale: PNG scaling factor.
        charts_path: Optional path to Helm charts repository.
        tab: Optional tab key to capture.
        keep_svg: If False, delete SVG after PNG conversion.
        all_tabs: If True, capture all tabs of the screen.
        skip_tabs: If True, skip keyboard tab discovery.
        scroll_vertical: If True, force vertical scroll capture. If False, disable.
        scroll_horizontal: If True, force horizontal scroll capture. If False, disable.
        skip_toggles: If True, skip toggle state capture.
        skip_inner_tabs: If True, skip TabbedContent inner tabs capture.
        skip_collapsibles: If True, skip collapsible widget capture.
        delays: List of delays in seconds for multi-delay capture.
        scroll_delay: Wait time between scroll positions.
        tab_delay: Wait time after switching tabs.
        timeout: Optional global timeout in seconds.

    Returns:
        list of captured file paths.

    """
    config = _create_config(
        output_dir, size, png_scale, keep_svg, charts_path,
        delays, scroll_delay, tab_delay, timeout,
    )

    engine = CaptureEngine(config)

    # Apply global timeout if specified
    capture_task = engine.capture_single_screen(
        screen_name=screen,
        tab=tab,
        all_tabs=all_tabs,
        skip_tabs=skip_tabs,
        scroll_vertical=scroll_vertical,
        scroll_horizontal=scroll_horizontal,
        skip_toggles=skip_toggles,
        skip_inner_tabs=skip_inner_tabs,
        skip_collapsibles=skip_collapsibles,
    )

    if timeout is not None and timeout > 0:
        files = await asyncio.wait_for(capture_task, timeout=timeout)
    else:
        files = await capture_task

    return files


async def _capture_all_screens_with_engine(
    output_dir: Path,
    size: tuple[int, int],
    png_scale: float = 1.0,
    charts_path: Path | None = None,
    keep_svg: bool = False,
    *,
    delays: list[float],
    scroll_delay: float = 0.3,
    tab_delay: float = 0.5,
    timeout: float | None = None,
) -> dict[str, list[Path]]:
    """Capture all screens using CaptureEngine with a single app instance.

    Args:
        output_dir: Directory to save screenshots.
        size: Terminal size as (columns, rows).
        png_scale: PNG scaling factor.
        charts_path: Optional path to Helm charts repository.
        keep_svg: If False, delete SVG after PNG conversion.
        delays: List of delays in seconds for multi-delay capture.
        scroll_delay: Wait time between scroll positions.
        tab_delay: Wait time after switching tabs.
        timeout: Optional global timeout in seconds.

    Returns:
        dict mapping screen names to lists of captured files.

    """
    config = _create_config(
        output_dir, size, png_scale, keep_svg, charts_path,
        delays, scroll_delay, tab_delay, timeout,
    )

    engine = CaptureEngine(config)
    _setup_progress_callbacks(engine)

    # Initialize discovery
    logger.info("Initializing discovery...")
    discovery = await engine.initialize()
    logger.info(f"Found {discovery.total_screens} screens to capture")

    # Capture all screens with single app instance
    logger.info("Starting capture...")

    async def run_capture_all() -> None:
        await engine.capture_all()

    if timeout is not None and timeout > 0:
        await asyncio.wait_for(run_capture_all(), timeout=timeout)
    else:
        await run_capture_all()

    return _build_results_dict(discovery.screens, output_dir)


async def _capture_selected_screens_with_engine(
    screen_names: list[str],
    output_dir: Path,
    size: tuple[int, int],
    png_scale: float = 1.0,
    charts_path: Path | None = None,
    keep_svg: bool = False,
    *,
    delays: list[float],
    scroll_delay: float = 0.3,
    tab_delay: float = 0.5,
    timeout: float | None = None,
) -> dict[str, list[Path]]:
    """Capture selected screens using CaptureEngine with a single app instance.

    Unlike _capture_all_screens_with_engine, this only captures the specified
    screens, making it more efficient when only a subset of screens need review.

    Args:
        screen_names: List of screen names to capture.
        output_dir: Directory to save screenshots.
        size: Terminal size as (columns, rows).
        png_scale: PNG scaling factor.
        charts_path: Optional path to Helm charts repository.
        keep_svg: If False, delete SVG after PNG conversion.
        delays: List of delays in seconds for multi-delay capture.
        scroll_delay: Wait time between scroll positions.
        tab_delay: Wait time after switching tabs.
        timeout: Optional global timeout in seconds.

    Returns:
        dict mapping screen names to lists of captured files.

    """
    config = _create_config(
        output_dir, size, png_scale, keep_svg, charts_path,
        delays, scroll_delay, tab_delay, timeout,
    )

    engine = CaptureEngine(config)
    _setup_progress_callbacks(engine)

    # Initialize discovery (needed for navigation)
    logger.info("Initializing discovery...")
    await engine.initialize()
    logger.info(f"Capturing {len(screen_names)} selected screens: {', '.join(screen_names)}")

    # Capture selected screens with single app instance
    logger.info("Starting capture...")

    async def run_capture_selected() -> None:
        await engine.capture_screens(screen_names)

    if timeout is not None and timeout > 0:
        await asyncio.wait_for(run_capture_selected(), timeout=timeout)
    else:
        await run_capture_selected()

    return _build_results_dict(screen_names, output_dir)


def _print_analysis_prompts(
    captured_files: list[Path],
    analysis_type: str,
    delays: list[float],
) -> None:
    """Print AI analysis prompts for captured screenshots.

    Args:
        captured_files: List of captured PNG file paths.
        analysis_type: Type of analysis to generate prompts for.
        delays: List of delays used during capture.
    """
    # Filter to only PNG files
    png_files = [f for f in captured_files if f.suffix.lower() == ".png"]

    if not png_files:
        logger.warning("No PNG files found for analysis.")
        return

    print("\n" + "=" * 70)
    print("AI ANALYSIS PROMPTS")
    print("=" * 70)
    print(f"\nAnalysis type: {analysis_type}")
    print(f"Files to analyze: {len(png_files)}")
    print("\nUse these prompts with Claude Code's Read tool (native multimodal vision):\n")

    # Group files by screen
    files_by_screen: dict[str, list[Path]] = {}
    for f in png_files:
        screen_name = f.parent.name
        if screen_name not in files_by_screen:
            files_by_screen[screen_name] = []
        files_by_screen[screen_name].append(f)

    for screen_name, files in files_by_screen.items():
        print("-" * 70)
        print(f"SCREEN: {screen_name.upper()}")
        print("-" * 70)

        # Get the primary screenshot (usually the base or first one)
        primary_file = files[0]

        # Determine delay from filename if possible
        delay_seconds: float | None = None
        for delay in delays:
            delay_str = f"{int(delay):03d}s"
            if delay_str in primary_file.name:
                delay_seconds = delay
                break

        # Generate prompt
        prompt = generate_analysis_prompt(
            screen_name=screen_name,
            analysis_type=analysis_type,
            delay_seconds=delay_seconds,
        )

        print(f"\nFile: {primary_file}")
        print("\nPrompt:")
        print("-" * 40)
        # Print first 500 chars with ellipsis if longer
        if len(prompt) > 500:
            print(prompt[:500] + "\n...[truncated]")
        else:
            print(prompt)
        print("-" * 40)

        print("\n# Claude Code native multimodal vision - just read the image:")
        print(f'Read(file_path="{primary_file}")')
        print("# Then analyze using the prompt context above")

        # If multiple files, list all
        if len(files) > 1:
            print(f"\nAll files for {screen_name}:")
            for f in files:
                print(f"  - {f}")

        print()

    print("=" * 70)
    print("END OF ANALYSIS PROMPTS")
    print("=" * 70)
