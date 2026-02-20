"""CustomHeader widget - standardized wrapper around Textual's Header."""

from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING

from textual.containers import Container
from textual.events import Resize
from textual.timer import Timer
from textual.widgets import Header as TextualHeader

from kubeagle.widgets.display.custom_static import CustomStatic

if TYPE_CHECKING:
    from textual.app import ComposeResult


class CustomHeader(Container):
    """Standardized header wrapper around Textual's Header.

    Provides consistent styling and integration with the TUI design system.
    Wraps Textual's built-in Header widget.

    Title is controlled via app.title / app.sub_title.
    Clock is controlled via Header's auto_clock functionality.

    CSS Classes: widget-custom-header

    Note: DEFAULT_CSS is used instead of CSS_PATH for self-targeting rules
    because SCOPED_CSS (True by default) prevents CSS_PATH rules from
    applying to the widget itself -- they only apply to descendants.
    """

    CSS_PATH = "../../css/widgets/custom_header.tcss"
    _RESIZE_BADGE_DEBOUNCE_SECONDS = 0.05

    DEFAULT_CSS = """
    CustomHeader {
        dock: top;
        height: 1;
        width: 100%;
        overflow: hidden hidden;
    }
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.add_class("widget-custom-header")
        self._resize_badge_timer: Timer | None = None

    def compose(self) -> ComposeResult:
        """Compose the header with Textual's Header widget."""
        yield TextualHeader()

    async def on_mount(self) -> None:
        """Mount and initialize the terminal-size badge."""
        await self._ensure_terminal_size_badge()
        self._schedule_terminal_size_badge_update()

    def on_resize(self, _: Resize) -> None:
        """Keep the terminal-size badge synchronized with app dimensions."""
        self._schedule_terminal_size_badge_update()
        with suppress(Exception):
            enforce_terminal_size = getattr(
                self.app, "_enforce_terminal_size_policy", None,
            )
            if callable(enforce_terminal_size):
                self.app.call_after_refresh(enforce_terminal_size)

    def on_unmount(self) -> None:
        """Cancel pending debounce timer on widget unmount."""
        if self._resize_badge_timer is not None:
            self._resize_badge_timer.stop()
            self._resize_badge_timer = None

    def _schedule_terminal_size_badge_update(self) -> None:
        """Debounce badge updates while the terminal is resizing."""
        if self._resize_badge_timer is not None:
            self._resize_badge_timer.stop()
            self._resize_badge_timer = None

        self._resize_badge_timer = self.set_timer(
            self._RESIZE_BADGE_DEBOUNCE_SECONDS,
            self._run_debounced_terminal_size_badge_update,
        )

    def _run_debounced_terminal_size_badge_update(self) -> None:
        self._resize_badge_timer = None
        self._update_terminal_size_badge()

    def _update_terminal_size_badge(self) -> None:
        """Display terminal size in WIDTHxHEIGHT format."""
        with suppress(Exception):
            self.query_one("#terminal-size-badge", CustomStatic).update(
                f"{self.app.size.width}x{self.app.size.height}",
            )

    async def _ensure_terminal_size_badge(self) -> None:
        """Mount the terminal-size badge inside the header once."""
        with suppress(Exception):
            self.query_one("#terminal-size-badge", CustomStatic)
            return

        with suppress(Exception):
            header = self.query_one(TextualHeader)
            badge = CustomStatic("", id="terminal-size-badge")
            # Badge is mounted dynamically; apply essential layout styles directly
            # to avoid scoped stylesheet misses.
            badge.styles.dock = "right"
            badge.styles.width = "auto"
            badge.styles.min_width = 10
            badge.styles.height = 1
            badge.styles.padding = (0, 1, 0, 1)
            badge.styles.margin = (0, 0, 0, 0)
            badge.styles.text_align = "right"
            badge.styles.content_align = ("right", "middle")
            badge.styles.text_style = "bold"
            await header.mount(badge)
