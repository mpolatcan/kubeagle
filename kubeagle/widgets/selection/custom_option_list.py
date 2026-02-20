"""CustomOptionList widget for the TUI application.

Standard Wrapper Pattern:
- Wraps Textual's OptionList with standardized styling
- Supports option selection and highlighting
- Configurable height and item count

CSS Classes: widget-custom-option-list
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, cast

from rich.segment import Segment
from textual.containers import Container
from textual.geometry import Region, Size
from textual.strip import Strip
from textual.style import Style
from textual.visual import Padding
from textual.widgets import OptionList as TextualOptionList
from textual.widgets.option_list import Option

if TYPE_CHECKING:
    from textual.app import ComposeResult


class CustomOptionList(Container):
    """Standardized option list wrapper around Textual's OptionList widget.

    Provides consistent styling and integration with the TUI design system.
    Wraps Textual's built-in OptionList widget with standardized CSS classes.

    CSS Classes: widget-custom-option-list

    Features:
        - Keyboard navigation (up/down, page up/down, first/last)
        - Selection with Enter key
        - Option enable/disable support
        - Separator support between options
        - Highlight and selection events

    Example:
        ```python
        option_list = CustomOptionList(
            options=["Option 1", "Option 2", "Option 3"],
            id="my-options"
        )
    ```
    """

    CSS_PATH = "../../css/widgets/custom_option_list.tcss"

    class _ScrollableOptionList(TextualOptionList):
        """OptionList variant that preserves natural content width for x-scroll."""

        def render_line(self, y: int) -> Strip:
            """Render a line and apply horizontal crop based on the current scroll offset."""
            strip = super().render_line(y)
            content_region = self.scrollable_content_region
            if not content_region:
                return strip
            scroll_x = int(self.scroll_offset.x)
            if scroll_x <= 0:
                return strip
            return strip.crop(scroll_x, scroll_x + int(content_region.width))

        def _horizontal_render_width(self) -> int:
            if not self.scrollable_content_region:
                return 0
            content_width = self.get_content_width(
                self.scrollable_content_region.size,
                self.scrollable_content_region.size,
            )
            return max(
                int(self.scrollable_content_region.width),
                int(content_width),
            )

        def get_content_width(self, container: Size, viewport: Size) -> int:
            expanded_width = max(container.width, viewport.width, 4096)
            return super().get_content_width(
                Size(expanded_width, container.height),
                viewport,
            )

        def _update_lines(self) -> None:
            if not self.scrollable_content_region:
                return
            line_cache = self._line_cache
            lines = line_cache.lines
            next_index = lines[-1][0] + 1 if lines else 0
            get_visual = self._get_visual
            styles = cast(Any, self.styles)
            width = max(1, self._horizontal_render_width() - self._get_left_gutter_width())
            if next_index < len(self.options):
                padding = self.get_component_styles("option-list--option").padding
                for index, option in enumerate(self.options[next_index:], next_index):
                    line_cache.index_to_line[index] = len(line_cache.lines)
                    line_count = (
                        get_visual(option).get_height(styles, width - padding.width)
                        + option._divider
                    )
                    line_cache.heights[index] = line_count
                    line_cache.lines.extend(
                        [(index, line_no) for line_no in range(0, line_count)]
                    )
            last_divider = self.options and self.options[-1]._divider
            virtual_size = Size(width, len(lines) - (1 if last_divider else 0))
            target_width = self._horizontal_render_width()
            if target_width != getattr(self, "_last_render_width", 0):
                self._option_render_cache.clear()
                self._last_render_width = target_width
            if virtual_size != self.virtual_size:
                self.virtual_size = virtual_size
                self._scroll_update(virtual_size)

        def _get_option_render(self, option: Any, style: Style) -> list[Strip]:
            """Render options at natural width so x-scroll can expose long values."""
            padding = self.get_component_styles("option-list--option").padding
            render_width = self._horizontal_render_width()
            width = max(1, render_width - self._get_left_gutter_width())
            cache_key = (option, style, padding)
            strips = self._option_render_cache.get(cache_key)
            if strips is None:
                visual = self._get_visual(option)
                if padding:
                    visual = Padding(visual, padding)
                strips = visual.to_strips(self, visual, width, None, style)
                meta = {"option": self._option_to_index[option]}
                strips = [
                    strip.extend_cell_length(width, style.rich_style).apply_meta(meta)
                    for strip in strips
                ]
                if option._divider:
                    separator_style = self.get_visual_style("option-list--separator")
                    strips.append(
                        Strip([Segment("─" * width, separator_style.rich_style)], width)
                    )
                self._option_render_cache[cache_key] = strips
            return strips

        def scroll_to_highlight(self, top: bool = False) -> None:
            """Scroll highlighted row vertically while preserving horizontal offset."""
            highlighted = self.highlighted
            if highlighted is None or not self.is_mounted:
                return

            self._update_lines()
            try:
                y = self._index_to_line[highlighted]
                height = self._heights[highlighted]
            except KeyError:
                return

            self.scroll_to_region(
                Region(
                    int(self.scroll_x),
                    y,
                    self.scrollable_content_region.width,
                    height,
                ),
                force=True,
                animate=False,
                top=top,
                immediate=True,
            )

    def __init__(
        self,
        options: list[str] | list[Option] | None = None,
        id: str | None = None,
        classes: str = "",
        disabled: bool = False,
    ) -> None:
        """Initialize the custom option list wrapper.

        Args:
            options: List of option strings or Option instances.
            id: Widget ID.
            classes: CSS classes (widget-custom-option-list is automatically added).
            disabled: Whether the option list is disabled.
        """
        super().__init__(id=id, classes=f"widget-custom-option-list {classes}".strip())
        self._options = options or []
        self._disabled = disabled
        self._option_list: TextualOptionList | None = None

    def compose(self) -> ComposeResult:
        """Compose the option list with Textual's OptionList widget."""
        self._option_list = self._ScrollableOptionList(
            *self._options,
            id=self.id,
            disabled=self._disabled,
        )
        self._option_list.styles.scrollbar_size_horizontal = 1
        self._option_list.styles.scrollbar_size_vertical = 2
        yield self._option_list

    @property
    def option_list(self) -> TextualOptionList:
        """Get the underlying Textual OptionList widget.

        Returns:
            The composed Textual OptionList widget.
        """
        assert self._option_list is not None, "option_list accessed before mount"
        return self._option_list

    @property
    def options(self) -> Sequence[Option]:
        """Get the list of options.

        Returns:
            Sequence of Option objects.
        """
        return self.option_list.options

    @options.setter
    def options(self, value: list[str] | list[Option]) -> None:
        """Set the options.

        Args:
            value: New list of option strings or Option instances.
        """
        self.option_list.clear_options()
        if value:
            self.option_list.add_options(value)

    @property
    def highlighted(self) -> int | None:
        """Get the index of the currently highlighted option.

        Returns:
            The highlighted option index, or None if no option is highlighted.
        """
        return self.option_list.highlighted

    @highlighted.setter
    def highlighted(self, value: int) -> None:
        """Set the highlighted option by index.

        Args:
            value: Index to highlight.
        """
        self.option_list.highlighted = value

    @property
    def highlighted_option(self) -> Option | None:
        """Get the currently highlighted option.

        Returns:
            The highlighted Option, or None if no option is highlighted.
        """
        return self.option_list.highlighted_option

    def add_option(self, option: str | Option) -> None:
        """Add a single option to the list.

        Args:
            option: Option string or Option instance to add.
        """
        if isinstance(option, str):
            self.option_list.add_option(Option(option))
        else:
            self.option_list.add_option(option)

    def add_options(self, options: list[str] | list[Option]) -> None:
        """Add multiple options to the list.

        Args:
            options: List of option strings or Option instances.
        """
        processed_options = [
            opt if isinstance(opt, Option) else Option(opt)
            for opt in options
        ]
        self.option_list.add_options(processed_options)

    def remove_option(self, option_id: str) -> None:
        """Remove an option by its ID.

        Args:
            option_id: ID of the option to remove.
        """
        self.option_list.remove_option(option_id)

    def clear_options(self) -> None:
        """Clear all options from the list."""
        self.option_list.clear_options()

    def disable_option(self, option_id: str) -> None:
        """Disable an option by its ID.

        Args:
            option_id: ID of the option to disable.
        """
        self.option_list.disable_option(option_id)

    def enable_option(self, option_id: str) -> None:
        """Enable an option by its ID.

        Args:
            option_id: ID of the option to enable.
        """
        self.option_list.enable_option(option_id)

    def get_option(self, option_id: str) -> Option | None:
        """Get an option by its ID.

        Args:
            option_id: ID of the option to retrieve.

        Returns:
            The Option, or None if not found.
        """
        return self.option_list.get_option(option_id)

    def get_option_at_index(self, index: int) -> Option | None:
        """Get an option by its index.

        Args:
            index: Index of the option to retrieve.

        Returns:
            The Option, or None if not found.
        """
        return self.option_list.get_option_at_index(index)
