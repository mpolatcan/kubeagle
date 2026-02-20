"""CustomRadioSet widget - standardized wrapper around Textual's RadioSet."""

from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING

from textual.containers import Container
from textual.css.query import NoMatches
from textual.widgets import (
    RadioButton as TextualRadioButton,
    RadioSet as TextualRadioSet,
)

if TYPE_CHECKING:
    from textual.app import ComposeResult


class CustomRadioSet(Container):
    """Standardized radio set wrapper around Textual's RadioSet widget.

    Provides consistent styling and integration with the TUI design system.
    Wraps Textual's built-in RadioSet widget with standardized CSS classes.

    CSS Classes: widget-custom-radio-set

    Example:
        ```python
        CustomRadioSet(
            ["Option A", "Option B", "Option C"],
            id="options",
            classes="widget-custom-radio-set"
        )
    ```
    """

    CSS_PATH = "../../css/widgets/custom_radio_set.tcss"

    def __init__(
        self,
        *labels: str,
        id: str | None = None,
        classes: str = "",
        disabled: bool = False,
        compact: bool = False,
    ) -> None:
        """Initialize the custom radio set wrapper.

        Args:
            labels: Radio button labels.
            id: Widget ID.
            classes: CSS classes (widget-custom-radio-set is automatically added).
            disabled: Whether the radio set is disabled.
            compact: Whether to render in compact form.
        """
        super().__init__(id=id, classes=f"widget-custom-radio-set {classes}".strip())
        self._labels = labels
        self._disabled = disabled
        self._compact = compact
        self._pressed_index = 0

    def compose(self) -> ComposeResult:
        """Compose the radio set with Textual's RadioSet widget."""
        inner_id = f"{self.id}-inner" if self.id else None
        radio_set = TextualRadioSet(
            *self._labels,
            id=inner_id,
            disabled=self._disabled,
            compact=self._compact,
        )
        yield radio_set

    def on_mount(self) -> None:
        """Apply stored pressed index when mounted."""
        radio_set = self._get_radio_set()
        if radio_set is not None:
            self._apply_pressed_index(radio_set, self._pressed_index)

    @property
    def radio_set(self) -> TextualRadioSet:
        """Get the underlying Textual RadioSet widget.

        Returns:
            The composed Textual RadioSet widget.
        """
        return self.query_one(TextualRadioSet)

    def _get_radio_set(self) -> TextualRadioSet | None:
        """Safely get inner radio set, or None before compose/mount."""
        with suppress(NoMatches):
            return self.query_one(TextualRadioSet)
        return None

    def _apply_pressed_index(self, radio_set: TextualRadioSet, val: int) -> None:
        """Apply pressed index to the inner radio buttons."""
        buttons = list(radio_set.query(TextualRadioButton))
        if not buttons:
            return
        target = max(0, min(val, len(buttons) - 1))
        with suppress(Exception):
            buttons[target].value = True
        self._pressed_index = target

    @property
    def pressed_index(self) -> int:
        """Get the index of the currently pressed radio button.

        Returns:
            The index or -1 if none selected.
        """
        radio_set = self._get_radio_set()
        if radio_set is not None:
            return radio_set.pressed_index
        return self._pressed_index

    @pressed_index.setter
    def pressed_index(self, val: int) -> None:
        """Set the currently pressed radio button index.

        Args:
            val: The target pressed index.
        """
        self._pressed_index = max(0, val)
        radio_set = self._get_radio_set()
        if radio_set is not None:
            self._apply_pressed_index(radio_set, self._pressed_index)

    @property
    def value(self) -> int:
        """Get the current value (pressed index).

        Returns:
            The pressed index or -1.
        """
        return self.pressed_index

    @value.setter
    def value(self, val: int) -> None:
        """Set the current value (pressed index).

        Args:
            val: The target pressed index.
        """
        self.pressed_index = val

    @property
    def disabled(self) -> bool:
        """Get the disabled state.

        Returns:
            True if disabled, False otherwise.
        """
        radio_set = self._get_radio_set()
        return radio_set.disabled if radio_set is not None else self._disabled

    @disabled.setter
    def disabled(self, val: bool) -> None:
        """Set the disabled state.

        Args:
            val: New disabled state.
        """
        self._disabled = val
        radio_set = self._get_radio_set()
        if radio_set is not None:
            radio_set.disabled = val
