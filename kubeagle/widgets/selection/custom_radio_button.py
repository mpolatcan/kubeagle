"""CustomRadioButton widget - standardized wrapper around Textual's RadioButton."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.containers import Container
from textual.widgets import RadioButton as TextualRadioButton

if TYPE_CHECKING:
    from textual.app import ComposeResult


class CustomRadioButton(Container):
    """Standardized radio button wrapper around Textual's RadioButton widget.

    Provides consistent styling and integration with the TUI design system.
    Wraps Textual's built-in RadioButton widget with standardized CSS classes.

    CSS Classes: widget-custom-radio-button

    Example:
        ```python
        CustomRadioButton(
            "Option A",
            value=True,
            id="option-a",
            classes="widget-custom-radio-button"
        )
    ```
    """

    CSS_PATH = "../../css/widgets/custom_radio_button.tcss"

    def __init__(
        self,
        label: str = "",
        value: bool = False,
        id: str | None = None,
        classes: str = "",
        disabled: bool = False,
    ) -> None:
        """Initialize the custom radio button wrapper.

        Args:
            label: Label text for the radio button.
            value: Initial state (True for selected, False for unselected).
            id: Widget ID.
            classes: CSS classes (widget-custom-radio-button is automatically added).
            disabled: Whether the radio button is disabled.
        """
        super().__init__(id=id, classes=f"widget-custom-radio-button {classes}".strip())
        self._label = label
        self._value = value
        self._disabled = disabled
        self._radio_button: TextualRadioButton | None = None

    def compose(self) -> ComposeResult:
        """Compose the radio button with Textual's RadioButton widget."""
        radio = TextualRadioButton(
            self._label,
            value=self._value,
            id=self.id,
            disabled=self._disabled,
        )
        self._radio_button = radio
        yield radio

    @property
    def radio_button(self) -> TextualRadioButton | None:
        """Get the underlying Textual RadioButton widget.

        Returns:
            The composed Textual RadioButton widget, or None if not yet composed.
        """
        return self._radio_button

    @property
    def value(self) -> bool:
        """Get the current radio button state.

        Returns:
            True if selected, False otherwise.
        """
        if self._radio_button is None:
            return self._value
        return self._radio_button.value

    @value.setter
    def value(self, val: bool) -> None:
        """Set the radio button state.

        Args:
            val: New value (True for selected, False for unselected).
        """
        self._value = val
        if self._radio_button is not None:
            self._radio_button.value = val

    @property
    def label(self) -> str:
        """Get the label text.

        Returns:
            The label text.
        """
        if self._radio_button is None:
            return self._label
        return str(self._radio_button.label)

    @label.setter
    def label(self, val: str) -> None:
        """Set the label text.

        Args:
            val: New label text.
        """
        self._label = val
        if self._radio_button is not None:
            self._radio_button.label = val
