"""State-based capture engine for comprehensive TUI screenshots."""

from __future__ import annotations

import asyncio
import os
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from kubeagle.app import EKSHelmReporterApp
from loguru import logger
from textual.widgets import ContentSwitcher, Switch, TabbedContent

from tui_screenshot_capture.constants import (
    CAPTURE_MAX_RETRIES,
    FILENAME_SANITIZE_TABLE,
    INIT_SLEEP_DELAY,
    INIT_SLEEP_TIMEOUT,
    MAX_WIDGET_CACHE_SIZE,
    MAX_WIDGET_FIND_RETRIES,
    MIN_TABS_FOR_MULTI_TAB_CAPTURE,
    PNG_CONVERSION_TIMEOUT,
    RETRY_SLEEP_LONG,
    SCREENSHOT_TIMEOUT,
    SCROLL_CAPTURE_TIMEOUT,
    TAB_SWITCH_TIMEOUT,
    THREAD_JOIN_TIMEOUT,
    WIDGET_CACHE_EVICTION_MIN,
    WIDGET_FIND_RETRY_DELAY,
    get_canonical_name,
)
from tui_screenshot_capture.core import CaptureConfig, CaptureResult, TuiCaptureError
from tui_screenshot_capture.discovery import (
    CaptureStatus,
    DiscoveryResult,
    ScreenState,
    ScrollState,
    TabState,
    analyze_keyboard_tabs,
    analyze_screen_live,
    analyze_screen_scrollables,
    analyze_tab_scrollables,
    build_discovery_result,
    clear_visibility_cache,
    discover_focus_targets,
    discover_screens,
    discover_scrollable_widgets,
    discover_tabbed_content,
    discover_toggles,
)
from tui_screenshot_capture.utils import convert_svg_to_png

COLOR_FALLBACK_TERM = "xterm-256color"
COLOR_FALLBACK_COLORTERM = "truecolor"
COLOR_FALLBACK_FORCE_COLOR = "1"


class CaptureStuckError(Exception):
    """Raised when capture operation is stuck and needs app restart."""


class CaptureWatchdog:
    """Watchdog to prevent infinite hangs during capture.

    Uses a separate thread to monitor capture progress and raise
    an exception if the operation takes too long.
    """

    __slots__ = ("timeout", "operation_name", "_event", "_thread", "_cancelled", "_timed_out")

    def __init__(self, timeout: float, operation_name: str = "capture") -> None:
        """Initialize watchdog.

        Args:
            timeout: Maximum time allowed for operation in seconds.
            operation_name: Name of operation for error messages.

        """
        self.timeout = timeout
        self.operation_name = operation_name
        self._event = threading.Event()
        self._thread: threading.Thread | None = None
        self._cancelled = False
        self._timed_out = False

    def start(self) -> None:
        """Start watchdog timer.

        The watchdog monitors progress via pulse() calls. If pulse() is not
        called within the timeout, the watchdog triggers and check_and_raise()
        will raise CaptureStuckError.
        """
        self._cancelled = False
        self._timed_out = False
        self._event.clear()  # Clear so wait will block

        def watchdog_loop() -> None:
            """Watchdog thread that waits for event or timeout."""
            # wait() returns True if event was set before timeout, False otherwise
            if not self._event.wait(timeout=self.timeout):
                # Timeout - operation didn't make progress in time
                if not self._cancelled:
                    self._timed_out = True
                    logger.warning(
                        f"{self.operation_name} watchdog triggered after {self.timeout}s - operation may be stuck"
                    )
            # Thread exits here; next pulse() will start a new thread if needed

        self._thread = threading.Thread(target=watchdog_loop, daemon=True)
        self._thread.start()

    def pulse(self) -> None:
        """Indicate progress - resets the watchdog timer."""
        if not self._cancelled:
            self._event.set()

    def cancel(self) -> None:
        """Cancel watchdog - operation completed successfully."""
        self._cancelled = True
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=THREAD_JOIN_TIMEOUT)

    def timed_out(self) -> bool:
        """Check if watchdog timed out.

        Returns:
            True if watchdog triggered due to timeout.

        """
        return self._timed_out

    def check_and_raise(self) -> None:
        """Check if watchdog timed out and raise CaptureStuckError if so.

        Call this method during capture to detect stuck states.

        Raises:
            CaptureStuckError: If watchdog detected timeout.
        """
        if self._timed_out:
            raise CaptureStuckError(
                f"Capture operation stuck for {self.timeout}s - terminating and retrying"
            )


class CaptureEngine:
    """State-based capture engine for systematic TUI screenshot capture."""

    def __init__(self, config: CaptureConfig | None = None) -> None:
        """Initialize the capture engine.

        Args:
            config: Capture configuration. Uses defaults if not provided.

        """
        self.config = config or CaptureConfig()
        self.discovery: DiscoveryResult | None = None
        self.app: Any = None
        self.pilot: Any = None
        self.captured_files: list[Path] = []
        self._cached_screens: dict[str, str] | None = None

        # Cache for widget lookups to avoid repeated discovery (widget_id -> widget)
        self._widget_lookup_cache: dict[str, Any] = {}
        # Cache for discovered scrollable widgets per app instance (app_id -> scrollables list)
        self._scrollable_discovery_cache: dict[int, list[dict[str, Any]]] = {}
        # Widget lookup cache for O(1) access by widget_id (app_id -> {widget_id: scrollable})
        self._scrollable_id_index: dict[int, dict[str, dict[str, Any]]] = {}

        # Maximum widget cache size to prevent unbounded growth
        self._widget_cache_limit = MAX_WIDGET_CACHE_SIZE

        # Track app instance for cache invalidation
        self._app_instance_id: int | None = None

        # Clear visibility cache on new engine instance
        clear_visibility_cache()

        # Callbacks for progress reporting
        self.on_screen_start: Callable[[str], None] | None = None
        self.on_screen_complete: Callable[[str, ScreenState], None] | None = None
        self.on_capture: Callable[[str, Path], None] | None = None

    def _invalidate_widget_cache(self) -> None:
        """Clear widget cache when app state changes.

        Call this method when navigating between screens or when widgets
        may have been recreated (e.g., after tab switch).
        """
        self._widget_lookup_cache.clear()
        self._scrollable_discovery_cache.clear()
        self._scrollable_id_index.clear()
        self._app_instance_id = None
        clear_visibility_cache()  # Also clear visibility cache

    def _check_app_changed(self) -> bool:
        """Check if app instance changed and invalidate cache if so.

        Returns:
            True if app changed and cache was invalidated.
        """
        current_id = id(self.app) if self.app else None
        if current_id is not None and current_id != self._app_instance_id:
            self._invalidate_widget_cache()
            self._app_instance_id = current_id
            return True
        return False

    def _get_screens(self) -> dict[str, str]:
        """Get cached screens dictionary.

        Returns:
            Cached screens mapping screen_name -> nav_key.

        """
        if self._cached_screens is None:
            self._cached_screens = discover_screens()
        return self._cached_screens

    def _pulse_watchdog(self, watchdog: CaptureWatchdog | None) -> None:
        """Pulse the watchdog and check for stuck state.

        Args:
            watchdog: The watchdog to pulse. If None, no-op.

        """
        if watchdog is not None:
            watchdog.pulse()

    def _check_watchdog(self, watchdog: CaptureWatchdog | None) -> None:
        """Check if watchdog timed out and raise if so.

        Args:
            watchdog: The watchdog to check. If None, no-op.

        Raises:
            CaptureStuckError: If watchdog detected timeout.
        """
        if watchdog is not None:
            watchdog.check_and_raise()

    def _pulse_and_check_watchdog(self, watchdog: CaptureWatchdog | None) -> None:
        """Pulse watchdog and check for timeout in one call.

        Args:
            watchdog: The watchdog to pulse and check. If None, no-op.

        """
        if watchdog is not None:
            watchdog.pulse()
            watchdog.check_and_raise()

    async def _safe_sleep(self, delay: float, timeout: float) -> None:
        """Sleep with timeout protection.

        Args:
            delay: Sleep duration in seconds.
            timeout: Maximum time to allow for sleep.

        """
        try:
            await asyncio.wait_for(asyncio.sleep(delay), timeout=timeout)
        except asyncio.TimeoutError:
            pass  # Timeout is acceptable for delays

    def _ensure_color_environment(self) -> None:
        """Ensure terminal environment supports color screenshot export.

        Textual respects `NO_COLOR` and may downgrade rendering when `TERM=dumb`,
        which can produce grayscale screenshots in headless shells.
        """
        removed_no_color = os.environ.pop("NO_COLOR", None) is not None
        term = os.environ.get("TERM", "").strip().lower()

        term_updated = False
        if term in {"", "dumb"} or ("color" not in term and "xterm" not in term):
            os.environ["TERM"] = COLOR_FALLBACK_TERM
            term_updated = True

        colorterm = os.environ.get("COLORTERM", "").strip().lower()
        colorterm_updated = False
        if colorterm not in {"truecolor", "24bit"}:
            os.environ["COLORTERM"] = COLOR_FALLBACK_COLORTERM
            colorterm_updated = True

        force_color_updated = False
        for key in ("FORCE_COLOR", "CLICOLOR", "CLICOLOR_FORCE"):
            if os.environ.get(key) != COLOR_FALLBACK_FORCE_COLOR:
                os.environ[key] = COLOR_FALLBACK_FORCE_COLOR
                force_color_updated = True

        if removed_no_color or term_updated or colorterm_updated or force_color_updated:
            logger.info(
                "Adjusted terminal color environment for screenshot capture: "
                f"TERM={os.environ.get('TERM', '')}, "
                f"COLORTERM={os.environ.get('COLORTERM', '')}, "
                f"FORCE_COLOR={os.environ.get('FORCE_COLOR', '')}, "
                f"CLICOLOR={os.environ.get('CLICOLOR', '')}, "
                f"CLICOLOR_FORCE={os.environ.get('CLICOLOR_FORCE', '')}, "
                f"NO_COLOR={'unset' if removed_no_color else 'not-set'}"
            )

    async def initialize(self) -> DiscoveryResult:
        """Initialize discovery and return screen list.

        Returns:
            DiscoveryResult with all screens in PENDING status.

        """
        self.discovery = build_discovery_result()
        return self.discovery

    async def capture_single_screen(
        self,
        screen_name: str,
        tab: str | None = None,
        all_tabs: bool = False,
        skip_tabs: bool = False,
        scroll_vertical: bool | None = None,
        scroll_horizontal: bool | None = None,
        skip_toggles: bool = False,
        skip_inner_tabs: bool = False,
        skip_collapsibles: bool = False,
    ) -> list[Path]:
        """Capture a single screen with optional multi-delay support.

        Multi-delay capture:
        - At each delay, capture base screenshot with delay suffix (e.g., screen-030s.png)
        - Only at final delay, capture scroll positions, toggles, focus states, inner tabs, collapsibles

        Args:
            screen_name: Screen name to capture.
            tab: Optional tab key to capture.
            all_tabs: If True, capture all tabs of the screen.
            skip_tabs: If True, skip keyboard tab discovery.
            scroll_vertical: Override for vertical scroll capture.
            scroll_horizontal: Override for horizontal scroll capture.
            skip_toggles: If True, skip toggle capture.
            skip_inner_tabs: If True, skip inner tabs capture.
            skip_collapsibles: If True, skip collapsibles capture.

        Returns:
            List of captured file paths.

        """
        self.captured_files = []
        screens = self._get_screens()
        nav_screen = get_canonical_name(screen_name)
        delays = self.config.delays

        if nav_screen not in screens and nav_screen != "home":
            msg = f"Screen '{screen_name}' not found"
            logger.error(msg)
            raise TuiCaptureError(msg)

        # Capture timeout from config (global timeout for this capture)
        capture_timeout = self.config.capture_timeout
        # Use watchdog-based retry with kill-and-recreate
        max_retries = CAPTURE_MAX_RETRIES if capture_timeout > 0 else 1
        retry_timeout = min(capture_timeout / max_retries, 120) if capture_timeout > 0 else 0
        watchdog_timeout = max(retry_timeout / 2, 30) if capture_timeout > 0 else 180  # Max 3 min per attempt

        last_error: Exception | None = None

        for attempt in range(max_retries):
            # Clear visibility cache before starting new capture
            clear_visibility_cache()
            self._invalidate_widget_cache()

            # Create fresh app instance for each attempt
            self._ensure_color_environment()
            self.app = EKSHelmReporterApp(charts_path=self.config.charts_path)

            # Set up watchdog for this attempt
            watchdog = CaptureWatchdog(watchdog_timeout, f"Capture attempt {attempt + 1}")

            try:
                # Run capture with watchdog protection
                # The watchdog will detect if we get stuck and pulse() will reset it
                # Use default argument to bind watchdog at definition time (fixes B023)
                async def _execute_single_screen_capture(watchdog: CaptureWatchdog = watchdog) -> list[Path]:
                    return await self._do_capture_single_screen(
                        screen_name, nav_screen, screens, delays, tab, all_tabs,
                        skip_tabs, scroll_vertical, scroll_horizontal,
                        skip_toggles, skip_inner_tabs, skip_collapsibles,
                        watchdog
                    )

                if capture_timeout > 0:
                    async with asyncio.timeout(retry_timeout):  # type: ignore[attr-defined]
                        result = await _execute_single_screen_capture()
                else:
                    result = await _execute_single_screen_capture()

                # Success - cancel watchdog
                watchdog.cancel()
                return result

            except asyncio.TimeoutError as e:
                last_error = e
                watchdog.cancel()
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries}: capture timed out after {retry_timeout}s"
                )

            except CaptureStuckError as e:
                last_error = e
                watchdog.cancel()
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries}: capture stuck - {e}"
                )

            except TuiCaptureError as e:
                last_error = e
                watchdog.cancel()
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries}: capture error - {e}"
                )

            if attempt < max_retries - 1:
                logger.info(f"Retrying with fresh app instance (attempt {attempt + 2}/{max_retries})...")
                await asyncio.sleep(RETRY_SLEEP_LONG)  # Longer pause to ensure cleanup
            else:
                logger.error(f"All {max_retries} attempts failed")
                raise TuiCaptureError(
                    f"Capture failed after {max_retries} attempts (total timeout: {capture_timeout}s)"
                ) from last_error

        # Should never reach here
        raise TuiCaptureError("Unexpected capture failure") from last_error

    async def _do_capture_single_screen(
        self,
        screen_name: str,
        nav_screen: str,
        screens: dict[str, str],
        delays: list[float],
        tab: str | None = None,
        all_tabs: bool = False,
        skip_tabs: bool = False,
        scroll_vertical: bool | None = None,
        scroll_horizontal: bool | None = None,
        skip_toggles: bool = False,
        skip_inner_tabs: bool = False,
        skip_collapsibles: bool = False,
        watchdog: CaptureWatchdog | None = None,
    ) -> list[Path]:
        """Internal capture implementation.

        Args:
            screen_name: Screen name to capture.
            nav_screen: Canonical navigation screen name.
            screens: Screens dictionary.
            delays: List of delays for multi-delay capture.
            tab: Optional tab key to capture.
            all_tabs: If True, capture all tabs of the screen.
            skip_tabs: If True, skip keyboard tab discovery.
            scroll_vertical: Override for vertical scroll capture.
            scroll_horizontal: Override for horizontal scroll capture.
            skip_toggles: If True, skip toggle capture.
            skip_inner_tabs: If True, skip inner tabs capture.
            skip_collapsibles: If True, skip collapsibles capture.
            watchdog: Optional watchdog for detecting stuck state.

        Returns:
            List of captured file paths.

        """
        async with self.app.run_test(size=self.config.size) as pilot:
            self.pilot = pilot

            # Pulse watchdog immediately after app starts
            self._pulse_watchdog(watchdog)

            # Check for initialization errors - give time for async errors to propagate
            await self._safe_sleep(INIT_SLEEP_DELAY, INIT_SLEEP_TIMEOUT)

            self._check_watchdog(watchdog)

            # Verify app is functional - try to access screen
            screen = self.app.screen
            if screen is None:
                raise TuiCaptureError("App screen is None - initialization failed")

            # Navigate to screen
            if nav_screen != "home" and nav_screen in screens:
                await pilot.press(screens[nav_screen])
                # Wait for initial navigation delay with timeout protection
                await self._safe_sleep(delays[0], SCREENSHOT_TIMEOUT)
                # Invalidate widget cache on screen navigation
                self._invalidate_widget_cache()

            # Pulse watchdog after navigation
            self._pulse_watchdog(watchdog)

            # Build screen state
            screen_state = await self._build_screen_state(screen_name, nav_screen)

            # Check for stuck state after screen state build
            self._check_watchdog(watchdog)

            # Apply skip options
            if skip_tabs:
                screen_state.keyboard_tabs = []
            if skip_toggles:
                screen_state.toggles = []
            if skip_collapsibles:
                screen_state.collapsibles = []

            # Handle scroll overrides
            if scroll_vertical is False or scroll_horizontal is False:
                # Explicit disable - clear all scrollables
                screen_state.scrollables = []
            elif scroll_vertical is not None or scroll_horizontal is not None:
                # At least one override specified (True or None means auto-detect from max_scroll)
                for scroll in screen_state.scrollables:
                    if scroll_vertical is not None:
                        scroll.has_vertical = scroll_vertical and scroll.max_scroll_y > 0
                    if scroll_horizontal is not None:
                        scroll.has_horizontal = scroll_horizontal and scroll.max_scroll_x > 0

            # Get output directory
            output_dir = self.config.output_dir / screen_name
            output_dir.mkdir(parents=True, exist_ok=True)

            # Handle tab selection
            if tab:
                # Capture specific tab
                tabs_to_capture = [
                    t for t in screen_state.keyboard_tabs if t.tab_key == tab
                ]
                if not tabs_to_capture:
                    logger.error(f"Tab '{tab}' not found on screen '{screen_name}'")
                    return []

                screen_state.keyboard_tabs = tabs_to_capture
                await self._capture_keyboard_tab(
                    screen_state,
                    tabs_to_capture[0],
                    output_dir,
                )

            elif all_tabs:
                # Capture all tabs
                for tab_state in screen_state.keyboard_tabs:
                    await self._capture_keyboard_tab(
                        screen_state, tab_state, output_dir
                    )
            else:
                # Multi-delay capture: base screenshots at each delay, full capture at final
                is_final_delay = False
                for i, delay in enumerate(delays):
                    is_final_delay = (i == len(delays) - 1)

                    if i > 0:
                        # Wait for next delay with timeout protection
                        wait_time = delay - delays[i - 1]
                        await self._safe_sleep(wait_time, SCREENSHOT_TIMEOUT)

                    # Pulse watchdog at each delay iteration
                    self._pulse_watchdog(watchdog)

                    # Capture base screenshot with delay suffix
                    delay_suffix = f"{int(delay):03d}s"
                    await self._capture_base_with_suffix(screen_name, delay_suffix)

                    # At final delay, capture scroll positions, toggles, focus, inner tabs, collapsibles
                    if is_final_delay:
                        await self._capture_screen_with_options(
                            screen_state,
                            skip_inner_tabs=skip_inner_tabs,
                            skip_collapsibles=skip_collapsibles,
                            skip_focus=False,
                        )

        return self.captured_files

    async def _build_screen_state(
        self, screen_name: str, nav_screen: str
    ) -> ScreenState:
        """Build screen state for capture.

        Args:
            screen_name: Screen name.
            nav_screen: Navigation screen name (may be aliased).

        Returns:
            ScreenState with live discovery info.

        """
        screens = self._get_screens()
        nav_key = screens.get(nav_screen, "h")

        live_state = analyze_screen_live(self.app, screen_name, nav_key)

        # Build screen state from discovery result
        if self.discovery and screen_name in self.discovery.screens:
            screen_state = self.discovery.screens[screen_name]
            # Update with live state (overwrites binding-based discovery)
            screen_state.scrollables = live_state.scrollables
            screen_state.inner_tabs = live_state.inner_tabs
            screen_state.collapsibles = live_state.collapsibles
            screen_state.is_current = live_state.is_current
        else:
            screen_state = ScreenState(
                screen_name=screen_name,
                nav_key=nav_key,
                keyboard_tabs=analyze_keyboard_tabs(screen_name),
                focus_targets=discover_focus_targets(screen_name),
                toggles=discover_toggles(screen_name),
                scrollables=live_state.scrollables,
                inner_tabs=live_state.inner_tabs,
                collapsibles=live_state.collapsibles,
                is_current=live_state.is_current,
            )

        return screen_state

    async def _capture_screen_with_options(
        self,
        screen_state: ScreenState,
        skip_inner_tabs: bool = False,
        skip_focus: bool = False,
        skip_collapsibles: bool = False,
    ) -> None:
        """Capture screen with optional element skips.

        Args:
            screen_state: Screen state to capture.
            skip_inner_tabs: If True, skip inner tab capture and process keyboard tabs instead.
            skip_focus: If True, skip focus state capture.
            skip_collapsibles: If True, skip collapsible capture.

        """
        await self._capture_screen_impl(
            screen_state=screen_state,
            screen_name=screen_state.screen_name,
            prefer_inner_tabs=not skip_inner_tabs,
            skip_focus=skip_focus,
            skip_collapsibles=skip_collapsibles,
        )

    async def _capture_base_with_suffix(
        self,
        screen_name: str,
        delay_suffix: str,
    ) -> None:
        """Capture base screenshot with delay suffix.

        Args:
            screen_name: Screen name for directory.
            delay_suffix: Delay suffix for filename (e.g., '030s').

        """
        output_dir = self.config.output_dir / screen_name

        # Capture with delay suffix
        filename = f"{screen_name}-{delay_suffix}"
        await self._take_screenshot(output_dir, filename)

        # Update completed captures count if we have a screen state
        if self.discovery and screen_name in self.discovery.screens:
            self.discovery.screens[screen_name].completed_captures += 1

    async def capture_all(self) -> DiscoveryResult:
        """Capture all screens with full discovery.

        Returns:
            DiscoveryResult with capture status for each screen.

        """
        if not self.discovery:
            self.discovery = await self.initialize()

        self.discovery.status = CaptureStatus.IN_PROGRESS
        screens = self._get_screens()

        # Sequential capture - single app instance
        await self._capture_all_sequential(screens)

        self.discovery.status = CaptureStatus.COMPLETED
        return self.discovery

    async def capture_screens(self, screen_names: list[str]) -> DiscoveryResult:
        """Capture selected screens with full discovery.

        Args:
            screen_names: List of screen names to capture.

        Returns:
            DiscoveryResult with capture status for each screen.

        """
        if not self.discovery:
            self.discovery = await self.initialize()

        self.discovery.status = CaptureStatus.IN_PROGRESS
        screens = self._get_screens()

        # Filter to only selected screens
        selected_screens = {
            name: state
            for name, state in self.discovery.screens.items()
            if name in screen_names
        }

        # Capture selected screens sequentially with single app instance
        await self._capture_selected_sequential(screens, selected_screens)

        self.discovery.status = CaptureStatus.COMPLETED
        return self.discovery

    async def _capture_selected_sequential(
        self,
        screens: dict[str, str],
        selected_screens: dict[str, ScreenState],
    ) -> None:
        """Capture selected screens sequentially using a single app instance.

        Args:
            screens: Dictionary of all screen names to nav keys.
            selected_screens: Dictionary of selected screen names to screen states.

        """
        if self.discovery is None:
            msg = "discovery must be initialized before capture"
            raise TuiCaptureError(msg)

        # Clear visibility cache before starting
        clear_visibility_cache()
        self._invalidate_widget_cache()

        self._ensure_color_environment()
        self.app = EKSHelmReporterApp(charts_path=self.config.charts_path)

        async with self.app.run_test(size=self.config.size) as pilot:
            self.pilot = pilot

            for screen_name, screen_state in selected_screens.items():
                if self.on_screen_start:
                    self.on_screen_start(screen_name)

                try:
                    screen_state.status = CaptureStatus.IN_PROGRESS

                    # Navigate to screen
                    nav_key = screen_state.nav_key
                    nav_screen = get_canonical_name(screen_name)

                    if nav_screen != "home" and nav_screen in screens:
                        await pilot.press(screens[nav_screen])
                        # Wait for initial navigation delay with timeout protection
                        await self._safe_sleep(self.config.delays[0], SCREENSHOT_TIMEOUT)
                        # Invalidate widget cache on screen navigation
                        self._invalidate_widget_cache()

                    # Analyze screen with live app
                    live_state = analyze_screen_live(
                        self.app, screen_name, nav_key
                    )

                    # Update discovery with live info
                    screen_state.scrollables = live_state.scrollables
                    screen_state.inner_tabs = live_state.inner_tabs
                    screen_state.collapsibles = live_state.collapsibles
                    screen_state.is_current = live_state.is_current

                    # Capture the screen
                    await self._capture_screen(screen_state)

                    screen_state.status = CaptureStatus.COMPLETED
                    self.discovery.mark_screen_complete(screen_name)

                except asyncio.TimeoutError:
                    screen_state.status = CaptureStatus.FAILED
                    screen_state.error_message = f"Timeout after {SCREENSHOT_TIMEOUT}s"
                    logger.error(f"Error capturing {screen_name}: timeout")
                except Exception as e:
                    screen_state.status = CaptureStatus.FAILED
                    screen_state.error_message = str(e)
                    logger.error(f"Error capturing {screen_name}: {e}")

                if self.on_screen_complete:
                    self.on_screen_complete(screen_name, screen_state)

    async def _capture_all_sequential(self, screens: dict[str, str]) -> None:
        """Capture all screens sequentially using a single app instance.

        Args:
            screens: Dictionary of screen names to nav keys.

        """
        if self.discovery is None:
            msg = "discovery must be initialized before capture"
            raise TuiCaptureError(msg)

        await self._capture_selected_sequential(screens, self.discovery.screens)

    async def _capture_screen(
        self,
        screen_state: ScreenState,
    ) -> None:
        """Capture a single screen with all its elements.

        Args:
            screen_state: The screen state to capture.

        """
        screen_name = screen_state.screen_name
        await self._capture_screen_impl(screen_state, screen_name)

    async def _capture_screen_impl(
        self,
        screen_state: ScreenState,
        screen_name: str,
        prefer_inner_tabs: bool = True,
        skip_focus: bool = False,
        skip_collapsibles: bool = False,
    ) -> None:
        """Internal implementation of screen capture.

        Args:
            screen_state: The screen state to capture.
            screen_name: The screen name.
            prefer_inner_tabs: If True, process inner tabs when available.
                If False, process keyboard tabs instead.
            skip_focus: If True, skip focus state capture.
            skip_collapsibles: If True, skip collapsible capture.

        """
        screen_name_lower = screen_name.lower()  # Cache lowercase version
        screen_state.status = CaptureStatus.IN_PROGRESS
        screen_dir = self.config.output_dir / screen_name
        screen_dir.mkdir(parents=True, exist_ok=True)

        # 1. Capture base screenshot
        await self._take_screenshot(screen_dir, screen_name_lower)
        screen_state.completed_captures += 1

        # 2. Capture scroll positions for visible scrollables (in active tab)
        await self._capture_scrollables(
            screen_state.scrollables, screen_dir, screen_name_lower
        )

        # 3. Process tabs (inner tabs or keyboard tabs based on prefer_inner_tabs)
        has_inner_tabs = bool(screen_state.inner_tabs)

        if prefer_inner_tabs and has_inner_tabs:
            logger.info("Processing inner tabs with their scrollables")
            # Process inner tabs (TabbedContent) - each tab gets its own screenshot
            await self._capture_inner_tabs(screen_state, screen_dir)
        else:
            # Process keyboard tabs
            for tab in screen_state.keyboard_tabs:
                await self._capture_keyboard_tab(screen_state, tab, screen_dir)

        # 4. Capture toggles
        await self._capture_toggles(screen_state, screen_dir)

        # 5. Capture focus states
        if not skip_focus:
            await self._capture_focus_states(screen_state, screen_dir)

        # 6. Capture collapsibles
        if not skip_collapsibles:
            await self._capture_collapsibles(screen_state, screen_dir)

        screen_state.status = CaptureStatus.COMPLETED

    @staticmethod
    def _is_scroll_complete(
        scroll: ScrollState, axis: str
    ) -> bool:
        """Check if all positions for a scroll axis have been captured."""
        positions = getattr(scroll, f"scroll_positions_{axis}")
        captured = getattr(scroll, f"captured_positions_{axis}")
        return not positions or len(captured) == len(positions)

    async def _capture_scrollables(
        self,
        scrollables: list[ScrollState],
        output_dir: Path,
        prefix: str,
    ) -> None:
        """Capture scroll positions for a list of scrollables.

        Args:
            scrollables: List of scroll states to capture.
            output_dir: Directory to save screenshots.
            prefix: Filename prefix.

        """
        for scroll in scrollables:
            if not scroll.has_vertical and not scroll.has_horizontal:
                continue

            # Use widget reference directly from ScrollState
            # This is more reliable than lookup, especially for Screen widgets
            widget = scroll.widget
            if not widget:
                # Fallback to lookup for backwards compatibility
                widget = self._get_widget_by_id(scroll.widget_id)
            if not widget:
                logger.warning(f"Cannot find widget '{scroll.widget_id}' for scroll capture")
                continue

            # Capture vertical scroll positions
            if scroll.has_vertical and scroll.scroll_positions_v:
                logger.info(
                    f"    Scrolling {scroll.widget_type} '{scroll.widget_id}' vertically"
                )
                await self._capture_scroll_positions(
                    widget,
                    scroll,
                    output_dir,
                    prefix,
                    "v",
                    scroll.scroll_positions_v,
                    scroll.captured_positions_v,
                )
                # Reset to top
                await self._reset_scroll_position(widget, y=True)

            # Capture horizontal scroll positions
            if scroll.has_horizontal and scroll.scroll_positions_h:
                logger.info(
                    f"    Scrolling {scroll.widget_type} '{scroll.widget_id}' horizontally"
                )
                await self._capture_scroll_positions(
                    widget,
                    scroll,
                    output_dir,
                    prefix,
                    "h",
                    scroll.scroll_positions_h,
                    scroll.captured_positions_h,
                )
                # Reset to left
                await self._reset_scroll_position(widget, x=True)

            # Update status based on capture completeness
            v_done = self._is_scroll_complete(scroll, "v")
            h_done = self._is_scroll_complete(scroll, "h")

            # Determine status: COMPLETED if all captures done, PARTIAL otherwise
            scroll.status = CaptureStatus.COMPLETED if v_done and h_done else CaptureStatus.PARTIAL

    async def _capture_scroll_positions(
        self,
        widget: Any,
        scroll: ScrollState,
        output_dir: Path,
        prefix: str,
        axis: str,
        positions: list[int],
        captured_positions: list[int],
    ) -> None:
        """Capture scroll positions for a single axis.

        Args:
            widget: The widget to scroll.
            scroll: The scroll state containing metadata.
            output_dir: Directory to save screenshots.
            prefix: Filename prefix.
            axis: 'v' for vertical, 'h' for horizontal.
            positions: List of scroll positions to capture.
            captured_positions: List to append captured positions to.

        """
        # Validate axis parameter
        if axis not in ("v", "h"):
            msg = f"Invalid axis '{axis}'. Must be 'v' (vertical) or 'h' (horizontal)."
            raise ValueError(msg)

        scroll_axis = "y" if axis == "v" else "x"

        # Pre-compute filename format based on whether widget has explicit ID
        if scroll.has_explicit_id:
            filename_prefix = f"{prefix}-{scroll.widget_id}-scroll-{axis}"
        else:
            filename_prefix = f"{prefix}-scroll-{axis}"

        # Pre-compute scroll delay to avoid repeated attribute access
        scroll_delay = self.config.scroll_delay

        # Batch capture: group consecutive positions and reduce context switches
        # Note: has_vertical/has_horizontal checks already validate scroll_to exists
        for i, pos in enumerate(positions):
            try:
                widget.scroll_to(**{scroll_axis: pos})

                # Wait for scroll with timeout protection
                await self._safe_sleep(scroll_delay, SCROLL_CAPTURE_TIMEOUT)

                filename = f"{filename_prefix}-{i + 1}"
                await self._take_screenshot(output_dir, filename)
                captured_positions.append(pos)

            except asyncio.TimeoutError:
                logger.warning(
                    f"Scroll capture timed out at {scroll_axis}={pos} after {SCROLL_CAPTURE_TIMEOUT}s"
                )
                scroll.status = CaptureStatus.PARTIAL
            except (AttributeError, ValueError, RuntimeError) as e:
                logger.warning(
                    f"Scroll capture failed at {scroll_axis}={pos}: {e}"
                )
                scroll.status = CaptureStatus.PARTIAL

    async def _reset_scroll_position(
        self, widget: Any, *, x: bool = False, y: bool = False
    ) -> None:
        """Reset widget scroll position to origin.

        Args:
            widget: The widget to reset.
            x: If True, reset horizontal scroll to 0.
            y: If True, reset vertical scroll to 0.

        """
        try:
            # scroll_to is already verified to exist via has_vertical/has_horizontal checks
            if x and y:
                widget.scroll_to(x=0, y=0)
            elif x:
                widget.scroll_to(x=0)
            elif y:
                widget.scroll_to(y=0)
        except (AttributeError, ValueError, RuntimeError) as e:
            logger.debug(f"Failed to reset scroll position: {e}")

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename by replacing unsafe characters.

        Args:
            filename: The filename to sanitize.

        Returns:
            Sanitized filename safe for filesystem use.

        """
        return filename.translate(FILENAME_SANITIZE_TABLE)

    async def _capture_keyboard_tab(
        self,
        screen_state: ScreenState,
        tab: TabState,
        output_dir: Path,
    ) -> None:
        """Capture a keyboard-accessible tab.

        Args:
            screen_state: Parent screen state.
            tab: Tab state to capture.
            output_dir: Directory to save screenshots.

        """
        if not tab.tab_key:
            return

        try:
            # Switch to tab
            await self.pilot.press(tab.tab_key)
            # Wait for tab switch with timeout protection
            await self._safe_sleep(self.config.tab_delay, TAB_SWITCH_TIMEOUT)
            # Invalidate widget cache on tab switch (widgets may be recreated)
            self._invalidate_widget_cache()
            tab.status = CaptureStatus.IN_PROGRESS

            # Take tab screenshot
            prefix = f"{screen_state.screen_name}-tab-{tab.tab_name}".lower()
            await self._take_screenshot(output_dir, prefix)
            screen_state.completed_captures += 1

            # Discover and capture scrollables in this tab
            tab_state = analyze_tab_scrollables(self.app, tab)

            # Capture scrollables first
            await self._capture_scrollables(tab_state.scrollables or [], output_dir, prefix)

            # Check if all scrollables were captured successfully
            # PARTIAL is acceptable (some positions may fail but others succeeded)
            any_failed = any(
                sc.status == CaptureStatus.FAILED for sc in tab_state.scrollables
            )
            tab_state.status = (
                CaptureStatus.FAILED if any_failed else CaptureStatus.COMPLETED
            )

        except asyncio.TimeoutError:
            tab.status = CaptureStatus.FAILED
            logger.warning(f"Tab '{tab.tab_name}' capture timed out after {TAB_SWITCH_TIMEOUT}s")
        except Exception as e:
            tab.status = CaptureStatus.FAILED
            logger.warning(f"Tab '{tab.tab_name}' capture failed: {e}")

    async def _capture_inner_tabs(
        self,
        screen_state: ScreenState,
        output_dir: Path,
    ) -> None:
        """Capture inner tabs (TabbedContent widgets).

        Args:
            screen_state: Parent screen state.
            output_dir: Directory to save screenshots.

        """
        # Re-discover inner tabs to get live widget references
        # discover_tabbed_content is synchronous, run in thread pool
        try:
            inner_tabs_raw = await asyncio.to_thread(discover_tabbed_content, self.app)
        except Exception as e:
            logger.warning(f"Failed to discover inner tabs: {e}")
            inner_tabs_raw = []

        logger.debug(
            f"Found {len(inner_tabs_raw)} TabbedContent/ContentSwitcher widgets"
        )

        # Filter out duplicate widgets (ContentSwitcher with same tabs as TabbedContent)
        # Skip ContentSwitcher if it has the same tab IDs as another widget
        seen_tab_ids: set[str] = set()
        processed_widgets: list[dict[str, Any]] = []

        for widget_info in inner_tabs_raw:
            widget_type = widget_info.get("widget_type", "TabbedContent")
            tabs = widget_info.get("tabs", [])
            widget_id = widget_info.get("widget_id", "")

            # Get tab IDs for this widget
            widget_tab_ids = {t.get("id", "") for t in tabs}

            # Skip ContentSwitcher if its tabs are a subset of already processed tabs
            # (This happens when TabbedContent wraps ContentSwitcher)
            if widget_type == "ContentSwitcher" and widget_tab_ids.issubset(
                seen_tab_ids
            ):
                logger.debug(f"Skipping {widget_id} - duplicate of processed widget")
                continue

            # Skip widgets without explicit ID if their tabs are a subset of already seen (avoid duplicates)
            has_explicit_id = widget_info.get("has_explicit_id", False)
            if not has_explicit_id and widget_tab_ids and widget_tab_ids.issubset(seen_tab_ids):
                logger.debug(f"Skipping {widget_id} - duplicate tab IDs")
                continue

            seen_tab_ids.update(widget_tab_ids)
            processed_widgets.append(widget_info)

        logger.debug(f"Processing {len(processed_widgets)} unique widgets")

        # Query all TabbedContent and ContentSwitcher widgets once for the inner tabs loop
        try:
            all_tabbed_contents = list(self.app.screen.query(TabbedContent))
            all_content_switchers = list(self.app.screen.query(ContentSwitcher))
        except (AttributeError, ValueError, RuntimeError) as e:
            logger.debug(f"Failed to query TabbedContent/ContentSwitcher widgets: {e}")
            all_tabbed_contents = []
            all_content_switchers = []

        for idx, widget_info in enumerate(processed_widgets):
            widget_id = widget_info.get("widget_id", "")
            tabs = widget_info.get("tabs", [])
            has_explicit_id = widget_info.get("has_explicit_id", False)
            widget_index = idx
            widget_type = widget_info.get("widget_type", "TabbedContent")

            logger.debug(
                f"Widget {widget_id} (type={widget_type}) has {len(tabs)} tabs"
            )

            if len(tabs) < MIN_TABS_FOR_MULTI_TAB_CAPTURE:
                logger.debug(f"Skipping {widget_id} - only {len(tabs)} tab(s)")
                continue

            logger.info(f"Processing {len(tabs)} inner tabs for {widget_id}")

            # Store tab IDs and labels - the tabs list won't change
            # Filter out empty tab_id to avoid issues
            tab_data = [
                (t.get("id", ""), t.get("label", "") or t.get("id", ""))
                for t in tabs
                if t.get("id", "")
            ]

            for tab_id, tab_label in tab_data:
                try:
                    # Use retry mechanism to find widget after recompose
                    widget = await self._find_widget_with_retry(
                        widget_id=widget_id,
                        widget_type=widget_type,
                        widget_index=widget_index,
                        has_explicit_id=has_explicit_id,
                        pre_queried_tabbed_contents=all_tabbed_contents,
                        pre_queried_content_switchers=all_content_switchers,
                    )

                    if widget is None:
                        logger.warning(f"Cannot find widget '{widget_id}' after recompose")
                        continue

                    # Switch to inner tab - use direct property assignment for reliability
                    logger.debug(f"Switching inner tab to '{tab_id}'")

                    # ContentSwitcher uses show() method, TabbedContent uses active property
                    if widget_type == "ContentSwitcher":
                        # ContentSwitcher doesn't have Tabs widgets, use show() method
                        try:
                            widget.show(tab_id)
                        except (AttributeError, ValueError, TypeError):
                            pass
                        # Check and set 'current' property separately for clarity
                        if hasattr(widget, "current"):
                            try:
                                widget.current = tab_id
                            except (AttributeError, ValueError, TypeError):
                                pass
                    else:
                        # TabbedContent: Set active property directly (most reliable)
                        # Skip click method as it fails in test mode with visible region errors
                        try:
                            widget.active = tab_id
                        except Exception as e:
                            logger.warning(f"Failed to set active tab: {e}")
                            # Try action method as fallback
                            try:
                                action_suffix = tab_id.replace("tab-", "")
                                action_name = f"action_switch_tab_{action_suffix}"
                                if hasattr(widget.parent, action_name):
                                    action = getattr(widget.parent, action_name)
                                    if asyncio.iscoroutinefunction(action):
                                        await action()
                                    else:
                                        action()
                            except Exception as e:
                                logger.debug(f"Action method failed: {e}")

                    # Wait for tab switch with timeout protection
                    await self._safe_sleep(self.config.tab_delay, TAB_SWITCH_TIMEOUT)

                    # Take screenshot - include widget index to prevent overwrites
                    # when multiple widgets have tabs with same labels
                    safe_label = self._sanitize_filename(tab_label)
                    # Add widget_index suffix to prevent filename collisions
                    # e.g., charts-overview-0.png and charts-overview-1.png
                    prefix = f"{screen_state.screen_name}-{safe_label}-{widget_index}".lower()
                    await self._take_screenshot(output_dir, prefix)
                    screen_state.completed_captures += 1

                    # After taking screenshot, discover and capture scrollables in this tab
                    # Clear visibility cache first since we switched tabs
                    clear_visibility_cache()

                    # Discover scrollables in current tab
                    tab_scrollables = analyze_screen_scrollables(self.app)

                    # Capture scroll positions
                    if tab_scrollables:
                        await self._capture_scrollables(tab_scrollables, output_dir, prefix)

                except Exception as e:
                    logger.warning(
                        f"Inner tab '{tab_label}' (id={tab_id}) capture failed: {e}"
                    )

        # Clear visibility cache ONCE after processing ALL widgets
        clear_visibility_cache()

    async def _capture_toggles(
        self,
        screen_state: ScreenState,
        output_dir: Path,
    ) -> None:
        """Capture toggle states.

        Args:
            screen_state: Parent screen state.
            output_dir: Directory to save screenshots.

        """
        # Query all switches once and build lookup dict (O(n) instead of O(n*m))
        try:
            all_switches = self.app.screen.query(Switch)
            switch_by_id = {sw.id: sw for sw in all_switches if getattr(sw, "id", None) is not None}
        except (AttributeError, ValueError, RuntimeError):
            switch_by_id = {}

        for toggle in screen_state.toggles:
            toggle_key = toggle.get("key")
            toggle_name = toggle.get("name", "")

            if not toggle_key:
                continue

            # Check if toggle widget exists and track original state
            toggle_widget = switch_by_id.get(toggle_name)
            original_was_on = getattr(toggle_widget, "value", False) if toggle_widget else False

            toggled = False  # Track if we actually performed any toggles

            try:
                # Capture ON state - only toggle if not already ON
                if toggle_widget is None or not original_was_on:
                    await self.pilot.press(toggle_key)
                    # Wait with timeout protection
                    await self._safe_sleep(self.config.tab_delay, TAB_SWITCH_TIMEOUT)
                    toggled = True

                await self._take_screenshot(output_dir, f"{screen_state.screen_name}-toggle-{toggle_name}-on".lower())
                screen_state.completed_captures += 1

                # Capture OFF state - toggle OFF since we just ensured it's ON
                if toggled:
                    await self.pilot.press(toggle_key)
                    await self._safe_sleep(self.config.tab_delay, TAB_SWITCH_TIMEOUT)

                await self._take_screenshot(output_dir, f"{screen_state.screen_name}-toggle-{toggle_name}-off".lower())
                screen_state.completed_captures += 1

            except (asyncio.TimeoutError, AttributeError, ValueError, RuntimeError) as e:
                logger.warning(f"Toggle '{toggle_name}' capture failed: {e}")
                # Reset to original state - only if we actually toggled
                if toggled and toggle_key and self.pilot:
                    try:
                        is_on = getattr(toggle_widget, "value", False) if toggle_widget else False
                        if is_on != original_was_on:
                            await self.pilot.press(toggle_key)
                            await asyncio.sleep(self.config.tab_delay)
                    except (AttributeError, ValueError, RuntimeError) as reset_err:
                        logger.debug(f"Failed to reset toggle '{toggle_name}' state: {reset_err}")

    async def _capture_focus_states(
        self,
        screen_state: ScreenState,
        output_dir: Path,
    ) -> None:
        """Capture focus states.

        Args:
            screen_state: Parent screen state.
            output_dir: Directory to save screenshots.

        """
        for focus in screen_state.focus_targets:
            focus_key = focus.get("key")
            focus_target = focus.get("target", "")

            if not focus_key:
                continue

            try:
                await self.pilot.press(focus_key)
                await self._safe_sleep(self.config.tab_delay, TAB_SWITCH_TIMEOUT)

                filename = f"{screen_state.screen_name}-focus-{focus_target}".lower()
                await self._take_screenshot(output_dir, filename)
                screen_state.completed_captures += 1

                # Unfocus
                await self.pilot.press("escape")
                await self._safe_sleep(self.config.tab_delay, TAB_SWITCH_TIMEOUT)

            except asyncio.TimeoutError:
                logger.warning(f"Focus '{focus_target}' capture timed out after {TAB_SWITCH_TIMEOUT}s")
            except Exception as e:
                logger.warning(f"Focus '{focus_target}' capture failed: {e}")

    async def _capture_collapsibles(
        self,
        screen_state: ScreenState,
        output_dir: Path,
    ) -> None:
        """Capture collapsible widget states.

        Args:
            screen_state: Parent screen state.
            output_dir: Directory to save screenshots.

        """
        for collapsible in screen_state.collapsibles:
            collapsible_id = collapsible.get("id", "")
            collapsible_widget = collapsible.get("widget")
            is_collapsed = collapsible.get("collapsed", True)

            if not collapsible_widget:
                continue

            # Track toggle method for reset and which method was used
            toggle_method: Callable[[], None] | None = None
            used_collapsed_attr = False

            try:
                # Current state
                state_suffix = "collapsed" if is_collapsed else "expanded"
                filename = self._sanitize_filename(
                    f"{screen_state.screen_name}-collapsible-{collapsible_id}-{state_suffix}"
                ).lower()
                await self._take_screenshot(output_dir, filename)
                screen_state.completed_captures += 1

                # Toggle state - check once and cache the result
                toggle_method = getattr(collapsible_widget, "toggle", None)
                has_collapsed_attr = hasattr(collapsible_widget, "collapsed")

                if toggle_method is not None:
                    toggle_method()
                elif has_collapsed_attr:
                    collapsible_widget.collapsed = not is_collapsed
                    used_collapsed_attr = True
                await self._safe_sleep(self.config.tab_delay, TAB_SWITCH_TIMEOUT)

                opposite_state = "expanded" if is_collapsed else "collapsed"
                filename = self._sanitize_filename(
                    f"{screen_state.screen_name}-collapsible-{collapsible_id}-{opposite_state}"
                ).lower()
                await self._take_screenshot(output_dir, filename)
                screen_state.completed_captures += 1

            except asyncio.TimeoutError:
                logger.warning(f"Collapsible '{collapsible_id}' capture timed out after {TAB_SWITCH_TIMEOUT}s")
            except Exception as e:
                logger.warning(f"Collapsible '{collapsible_id}' capture failed: {e}")
            finally:
                # Only reset state if we actually performed the toggle
                if (toggle_method is not None or used_collapsed_attr) and collapsible_widget and self.pilot:
                    try:
                        if used_collapsed_attr:
                            collapsible_widget.collapsed = is_collapsed
                        elif toggle_method:
                            toggle_method()
                        await asyncio.sleep(self.config.tab_delay)
                    except (AttributeError, ValueError, RuntimeError) as e:
                        logger.debug(f"Failed to reset collapsible '{collapsible_id}' state: {e}")

    async def _take_screenshot(self, output_dir: Path, filename: str) -> CaptureResult:
        """Take a screenshot and convert to PNG.

        Args:
            output_dir: Directory to save the file.
            filename: Base filename (without extension).

        Returns:
            CaptureResult with file path or error.

        """
        try:
            svg_path = output_dir / f"{filename}.svg"

            # Export screenshot with timeout protection
            svg_content = await asyncio.wait_for(
                asyncio.to_thread(self.app.export_screenshot),
                timeout=SCREENSHOT_TIMEOUT
            )

            # Write SVG with error handling
            try:
                svg_path.write_text(svg_content)
            except OSError as e:
                logger.error(f"Failed to write SVG file {svg_path}: {e}")
                return CaptureResult(success=False, error=f"Failed to write SVG file: {e}")

            # Only log success after confirming the file was written
            if svg_path.exists():
                logger.info(f"Captured: {output_dir.name}/{svg_path.name}")
            else:
                logger.error(f"SVG file was not created: {svg_path}")
                return CaptureResult(success=False, error="SVG file was not created after write")

            # Convert to PNG with timeout protection
            png_path = await asyncio.wait_for(
                asyncio.to_thread(convert_svg_to_png, svg_path, scale=self.config.png_scale, keep_svg=self.config.keep_svg),
                timeout=PNG_CONVERSION_TIMEOUT
            )

            # Only track files that actually exist on disk
            # If keep_svg=True, both SVG and PNG exist (or just SVG if conversion failed)
            # If keep_svg=False, only PNG exists (SVG deleted after successful conversion)
            # If conversion failed, SVG still exists on disk (not deleted)
            if png_path:
                self.captured_files.append(png_path)
                final_path = png_path
            elif svg_path.exists():
                # PNG conversion failed but SVG exists, track it as fallback
                self.captured_files.append(svg_path)
                final_path = svg_path
            else:
                # No files to track (should not happen normally)
                logger.warning(f"No file generated for {filename}")
                return CaptureResult(success=False, error="No file generated")

            if self.on_capture:
                self.on_capture(filename, final_path)

            return CaptureResult(success=True, file_path=final_path)

        except asyncio.TimeoutError:
            logger.error(f"Screenshot operation timed out after {SCREENSHOT_TIMEOUT + PNG_CONVERSION_TIMEOUT}s for {filename}")
            return CaptureResult(success=False, error=f"Timeout after {SCREENSHOT_TIMEOUT + PNG_CONVERSION_TIMEOUT}s")
        except Exception as e:
            # Clean up SVG file on error
            try:
                svg_path = output_dir / f"{filename}.svg"
                if svg_path.exists():
                    svg_path.unlink()
            except Exception as cleanup_err:
                logger.debug(f"Failed to clean up SVG file: {cleanup_err}")
            return CaptureResult(success=False, error=str(e))

    def _get_widget_by_id(self, widget_id: str) -> Any | None:
        """Get a widget by its ID.

        Uses cache for all lookups to avoid repeated expensive discovery.

        Args:
            widget_id: The widget ID.

        Returns:
            Widget instance or None if not found.

        """
        if not (self.app and self.app.screen):
            return None

        # Check if app changed (e.g., screen navigation) and invalidate cache
        self._check_app_changed()

        # Check cache first for all IDs (both synthetic and explicit)
        cached = self._widget_lookup_cache.get(widget_id)
        if cached is not None:
            return cached

        # Enforce cache size limit before adding new entries
        if len(self._widget_lookup_cache) >= self._widget_cache_limit:
            # Remove oldest entries (first 50 or 10% whichever is larger)
            # FIFO eviction: dict maintains insertion order in Python 3.7+
            evict_count = max(len(self._widget_lookup_cache) // 10, WIDGET_CACHE_EVICTION_MIN)
            for _ in range(evict_count):
                try:
                    first_key = next(iter(self._widget_lookup_cache))
                    del self._widget_lookup_cache[first_key]
                except (StopIteration, KeyError):
                    break

        # Try direct query by ID first (for explicit IDs)
        try:
            widget = self.app.screen.query_one(f"#{widget_id}")
            self._widget_lookup_cache[widget_id] = widget
            return widget
        except Exception as e:
            logger.debug(f"Query by ID '{widget_id}' failed: {e}")

        # Fall back to searching all scrollable widgets (with caching to avoid duplicate discovery)
        # This is only reached for synthetic IDs or when query_by_id fails
        app_id = id(self.app)
        if app_id not in self._scrollable_discovery_cache:
            scrollables_list = discover_scrollable_widgets(self.app, primary_only=False)
            self._scrollable_discovery_cache[app_id] = scrollables_list
            # Build O(1) lookup dict
            widget_map: dict[str, dict[str, Any]] = {}
            for s in scrollables_list:
                if s.get("id"):
                    widget_map[s["id"]] = s
            self._scrollable_id_index[app_id] = widget_map

        # O(1) lookup instead of O(n) linear search
        widget_id_map = self._scrollable_id_index.get(app_id, {})
        scrollable = widget_id_map.get(widget_id)
        if scrollable:
            widget = scrollable.get("widget")
            if widget is not None:  # Explicit None check before caching
                self._widget_lookup_cache[widget_id] = widget
                return widget

        return None

    async def _find_widget_with_retry(
        self,
        widget_id: str,
        widget_type: str,
        widget_index: int,
        has_explicit_id: bool,
        pre_queried_tabbed_contents: list[TabbedContent] | None = None,
        pre_queried_content_switchers: list[ContentSwitcher] | None = None,
        max_retries: int = MAX_WIDGET_FIND_RETRIES,
        retry_delay: float = WIDGET_FIND_RETRY_DELAY,
    ) -> Any | None:
        """Find a widget with retry mechanism for reliability after recompose.

        Args:
            widget_id: The widget ID to find.
            widget_type: The widget type (TabbedContent or ContentSwitcher).
            widget_index: The widget index for non-explicit-ID widgets.
            has_explicit_id: Whether the widget has an explicit ID.
            pre_queried_tabbed_contents: Pre-queried TabbedContent widgets (optional).
            pre_queried_content_switchers: Pre-queried ContentSwitcher widgets (optional).
            max_retries: Maximum number of retry attempts.
            retry_delay: Delay between retries in seconds.

        Returns:
            Widget instance or None if not found after retries.
        """
        for attempt in range(max_retries + 1):
            widget: Any | None = None

            if has_explicit_id:
                # Widget has an explicit ID, query by ID
                try:
                    widget = self.app.screen.query_one(f"#{widget_id}")
                except Exception:
                    pass

            if widget is None:
                # Use pre-queried widget lists if available, otherwise query
                all_widgets = (
                    pre_queried_content_switchers if widget_type == "ContentSwitcher" else pre_queried_tabbed_contents
                )

                # If no pre-queried lists, query now
                if not all_widgets:
                    try:
                        if widget_type == "ContentSwitcher":
                            all_widgets = self.app.screen.query(ContentSwitcher)
                        else:
                            all_widgets = self.app.screen.query(TabbedContent)
                    except Exception as e:
                        logger.debug(f"Failed to query {widget_type} widgets: {e}")

                if all_widgets and widget_index < len(all_widgets):
                    widget = all_widgets[widget_index]
                else:
                    # Widget index out of range - invalidate cache and retry
                    total = len(all_widgets) if all_widgets else 0
                    logger.debug(
                        f"Widget index {widget_index} out of range for {widget_type} "
                        f"(total: {total}), invalidating cache and retrying..."
                    )
                    self._invalidate_widget_cache()
                    all_widgets = None

            if widget is not None:
                return widget

            if attempt < max_retries:
                logger.debug(
                    f"Widget '{widget_id}' not found on attempt {attempt + 1}/{max_retries + 1}, retrying..."
                )
                await asyncio.sleep(retry_delay)

        logger.debug(f"Widget '{widget_id}' not found after {max_retries + 1} attempts")
        return None

    def get_summary(self) -> dict[str, Any]:
        """Get capture summary.

        Returns:
            Dictionary with capture statistics.

        """
        if not self.discovery:
            return {"status": "not_initialized"}

        return {
            "status": self.discovery.status.value,
            "total_files": len(self.captured_files),
            **self.discovery.to_summary(),
        }
