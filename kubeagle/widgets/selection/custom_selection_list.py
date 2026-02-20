"""CustomSelectionList widget - standardized wrapper around Textual's SelectionList."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast

from rich.segment import Segment
from textual.containers import Container
from textual.geometry import Region, Size
from textual.strip import Strip
from textual.style import Style
from textual.visual import Padding
from textual.widgets import SelectionList as TextualSelectionList
from textual.widgets._selection_list import Selection

if TYPE_CHECKING:
    from textual.app import ComposeResult


SelectionType = TypeVar("SelectionType")


class _ScrollableSelectionList(TextualSelectionList[SelectionType]):
    """SelectionList variant that preserves natural content width for x-scroll."""

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
        return super().get_content_width(Size(expanded_width, container.height), viewport)

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


class CustomSelectionList(Container, Generic[SelectionType]):
    """Standardized selection list wrapper around Textual's SelectionList widget.

    Provides consistent styling and integration with the TUI design system.
    Wraps Textual's built-in SelectionList widget with standardized CSS classes.

    CSS Classes: widget-custom-selection-list

    Example:
        ```python
        from textual.widgets import Selection

        selections = [
            Selection("Option A", value="a"),
            Selection("Option B", value="b"),
        ]
        CustomSelectionList(
            *selections,
            id="selections",
            classes="widget-custom-selection-list"
        )
    ```
    """

    CSS_PATH = "../../css/widgets/custom_selection_list.tcss"

    def __init__(
        self,
        *selections: Selection[SelectionType] | tuple,
        id: str | None = None,
        classes: str = "",
        disabled: bool = False,
        compact: bool = False,
    ) -> None:
        """Initialize the custom selection list wrapper.

        Args:
            selections: Selection items (Selection objects or tuples).
            id: Widget ID.
            classes: CSS classes (widget-custom-selection-list is automatically added).
            disabled: Whether the selection list is disabled.
            compact: Whether to render in compact form.
        """
        super().__init__(id=id, classes=f"widget-custom-selection-list {classes}".strip())
        self._selections = selections
        self._disabled = disabled
        self._compact = compact
        self._selection_list: TextualSelectionList[SelectionType] | None = None

    def compose(self) -> ComposeResult:
        """Compose the selection list with Textual's SelectionList widget."""
        inner_id = f"{self.id}-inner" if self.id else None
        self._selection_list = _ScrollableSelectionList(
            *self._selections,
            id=inner_id,
            disabled=self._disabled,
            compact=self._compact,
        )
        self._selection_list.styles.scrollbar_size_horizontal = 1
        self._selection_list.styles.scrollbar_size_vertical = 2
        yield self._selection_list

    @property
    def selection_list(self) -> TextualSelectionList[SelectionType] | None:
        """Get the underlying Textual SelectionList widget.

        Returns:
            The composed Textual SelectionList widget, or None if not yet composed.
        """
        return self._selection_list

    @property
    def selected(self) -> list[SelectionType]:
        """Get the selected values.

        Returns:
            List of selected values, or empty list if not composed.
        """
        if self._selection_list is None:
            return []
        return self._selection_list.selected

    @property
    def disabled(self) -> bool:
        """Get the disabled state.

        Returns:
            True if disabled, False otherwise.
        """
        if self._selection_list is None:
            return self._disabled
        return self._selection_list.disabled

    @disabled.setter
    def disabled(self, val: bool) -> None:
        """Set the disabled state.

        Args:
            val: New disabled state.
        """
        self._disabled = val
        if self._selection_list is not None:
            self._selection_list.disabled = val

    def select(self, selection: Selection[SelectionType] | SelectionType) -> None:
        """Select an item.

        Args:
            selection: Selection or value to select.
        """
        if self._selection_list is not None:
            self._selection_list.select(selection)
