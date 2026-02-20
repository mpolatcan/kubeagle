"""CustomCheckbox widget - standardized wrapper around Textual's Checkbox."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.containers import Container, Horizontal
from textual.widgets import Checkbox as TextualCheckbox, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult


class CustomCheckbox(Container):
    """Standardized checkbox wrapper around Textual's Checkbox widget.

    Provides consistent styling and integration with the TUI design system.
    Allows users to toggle boolean values.

    CSS Classes: widget-custom-checkbox

    Example:
        ```python
        checkbox = CustomCheckbox("Enable feature", id="feature-toggle")
        ```
    """

    CSS_PATH = "../../css/widgets/custom_checkbox.tcss"

    def __init__(
        self,
        label: str = "",
        value: bool = False,
        *,
        id: str | None = None,
        classes: str = "",
        disabled: bool = False,
    ) -> None:
        """Initialize the custom checkbox wrapper.

        Args:
            label: Label text displayed next to the checkbox.
            value: Initial boolean state.
            id: Widget ID.
            classes: CSS classes (widget-custom-checkbox is automatically added).
            disabled: Whether the checkbox is disabled.
        """
        super().__init__(id=id, classes=f"widget-custom-checkbox {classes}".strip())
        self._label = label
        self._value = value
        self._disabled = disabled
        self._checkbox: TextualCheckbox | None = None

    def compose(self) -> ComposeResult:
        """Compose the checkbox with Textual's Checkbox widget."""
        with Horizontal():
            yield TextualCheckbox(
                value=self._value,
                disabled=self._disabled,
                id=f"{self.id}-checkbox" if self.id else None,
            )
            if self._label:
                yield Static(self._label, classes="checkbox-label")

    def on_mount(self) -> None:
        """Store reference to inner checkbox widget after mounting."""
        self._checkbox = self.query_one(TextualCheckbox)

    @property
    def checkbox(self) -> TextualCheckbox:
        """Get the underlying Textual Checkbox widget.

        Returns:
            The composed Textual Checkbox widget.
        """
        assert self._checkbox is not None
        return self._checkbox

    @property
    def value(self) -> bool:
        """Get the current checkbox state.

        Returns:
            True if checked, False otherwise.
        """
        return self.checkbox.value

    @value.setter
    def value(self, val: bool) -> None:
        """Set the checkbox state.

        Args:
            val: New boolean value.
        """
        self.checkbox.value = val

    def toggle(self) -> None:
        """Toggle the checkbox state."""
        self.checkbox.value = not self.checkbox.value
