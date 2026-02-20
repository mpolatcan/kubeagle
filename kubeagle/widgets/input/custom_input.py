"""CustomInput widget - standardized wrapper around Textual's Input."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.containers import Container
from textual.message import Message
from textual.widgets import Input as TextualInput

if TYPE_CHECKING:
    from textual.app import ComposeResult


class CustomInput(Container):
    """Standardized input wrapper around Textual's Input widget.

    Provides consistent styling and integration with the TUI design system.
    Wraps Textual's built-in Input widget with standardized CSS classes.

    CSS Classes: widget-custom-input

    Example:
        ```python
        CustomInput(
            placeholder="Enter value...",
            id="username",
            classes="widget-custom-input"
        )
    ```
    """

    CSS_PATH = "css/widgets/custom_input.tcss"

    class Changed(Message):
        """Message emitted when the input value changes.

        Attributes:
            input: The CustomInput that changed.
            value: The new value.
        """

        def __init__(self, input: CustomInput, value: str) -> None:
            self.input = input
            self.value = value
            super().__init__()

    class Submitted(Message):
        """Message emitted when the input is submitted (Enter pressed).

        Attributes:
            input: The CustomInput that was submitted.
            value: The submitted value.
        """

        def __init__(self, input: CustomInput, value: str) -> None:
            self.input = input
            self.value = value
            super().__init__()

    def __init__(
        self,
        placeholder: str = "",
        value: str = "",
        id: str | None = None,
        classes: str = "",
        disabled: bool = False,
        password: bool = False,
        max_length: int = 0,
        restrict: str | None = None,
    ) -> None:
        """Initialize the custom input wrapper.

        Args:
            placeholder: Placeholder text displayed when empty.
            value: Initial value of the input.
            id: Widget ID.
            classes: CSS classes (widget-custom-input is automatically added).
            disabled: Whether the input is disabled.
            password: Whether to mask input as password.
            max_length: Maximum character length.
            restrict: Regex pattern to restrict input characters.
        """
        self._id = id
        self._inner_widget: TextualInput | None = None
        super().__init__(id=id, classes=f"widget-custom-input {classes}".strip())
        self._placeholder = placeholder
        self._value = value
        self._disabled = disabled
        self._password = password
        self._max_length = max_length
        self._restrict = restrict

    def compose(self) -> ComposeResult:
        """Compose the input with Textual's Input widget."""
        inner_id = f"{self._id}-inner" if self._id else None
        input_widget = TextualInput(
            placeholder=self._placeholder,
            value=self._value,
            id=inner_id,
            disabled=self._disabled,
            password=self._password,
            max_length=self._max_length,
            restrict=self._restrict,
        )
        self._inner_widget = input_widget
        yield input_widget

    @property
    def input(self) -> TextualInput:
        """Get the underlying Textual Input widget.

        Returns:
            The composed Textual Input widget.
        """
        if self._inner_widget is None:
            return self.query_one(TextualInput)
        return self._inner_widget

    @property
    def value(self) -> str:
        """Get the current input value.

        Returns:
            The input value.
        """
        return self.input.value

    @value.setter
    def value(self, val: str) -> None:
        """Set the input value.

        Args:
            val: New value to set.
        """
        self.input.value = val

    @property
    def placeholder(self) -> str:
        """Get the placeholder text.

        Returns:
            The placeholder text.
        """
        return str(self.input.placeholder)

    @placeholder.setter
    def placeholder(self, val: str) -> None:
        """Set the placeholder text.

        Args:
            val: New placeholder text.
        """
        self.input.placeholder = val

    def clear(self) -> None:
        """Clear the input value."""
        self.input.value = ""

    def _on_input_changed(self, event: TextualInput.Changed) -> None:
        """Handle input value changes and emit custom Changed message."""
        event.stop()
        self.post_message(self.Changed(self, event.value))

    def _on_input_submitted(self, event: TextualInput.Submitted) -> None:
        """Handle input submission and emit custom Submitted message."""
        event.stop()
        self.post_message(self.Submitted(self, event.value))
