"""CustomSwitch widget - standardized wrapper around Textual's Switch."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.containers import Container, Horizontal
from textual.widgets import Static, Switch as TextualSwitch

if TYPE_CHECKING:
    from textual.app import ComposeResult


class CustomSwitch(Container):
    """Standardized switch wrapper around Textual's Switch widget.

    Provides consistent styling and integration with the TUI design system.
    A toggle switch for boolean values with on/off states.

    CSS Classes: widget-custom-switch

    Example:
        ```python
        switch = CustomSwitch("Dark Mode", value=True, id="dark-mode-toggle")
        ```
    """

    CSS_PATH = "../../css/widgets/custom_switch.tcss"

    def __init__(
        self,
        label: str = "",
        value: bool = False,
        *,
        id: str | None = None,
        classes: str = "",
        disabled: bool = False,
    ) -> None:
        """Initialize the custom switch wrapper.

        Args:
            label: Label text displayed next to the switch.
            value: Initial boolean state.
            id: Widget ID.
            classes: CSS classes (widget-custom-switch is automatically added).
            disabled: Whether the switch is disabled.
        """
        super().__init__(id=id, classes=f"widget-custom-switch {classes}".strip())
        self._label = label
        self._value = value
        self._disabled = disabled
        self._switch: TextualSwitch | None = None

    def compose(self) -> ComposeResult:
        """Compose the switch with Textual's Switch widget."""
        with Horizontal():
            switch = TextualSwitch(
                value=self._value,
                disabled=self._disabled,
                id=f"{self.id}-switch" if self.id else None,
            )
            self._switch = switch
            yield switch
            if self._label:
                yield Static(self._label, classes="switch-label")

    @property
    def switch(self) -> TextualSwitch:
        """Get the underlying Textual Switch widget.

        Returns:
            The composed Textual Switch widget.
        """
        assert self._switch is not None, "Switch widget not composed yet"
        return self._switch

    @property
    def value(self) -> bool:
        """Get the current switch state.

        Returns:
            True if on, False if off.
        """
        return self.switch.value

    @value.setter
    def value(self, val: bool) -> None:
        """Set the switch state.

        Args:
            val: New boolean value.
        """
        self.switch.value = val

    def toggle(self) -> None:
        """Toggle the switch state."""
        self.switch.value = not self.switch.value
