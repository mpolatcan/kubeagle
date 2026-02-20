"""CustomButton widget for the TUI application.

Standard Wrapper Pattern:
- Wraps Textual's Button with standardized styling
- Supports variants: default, primary, success, warning, error
- Optional compact mode for dense layouts

CSS Classes: widget-custom-button
"""

from __future__ import annotations

from textual.events import Click
from textual.message import Message
from textual.widgets import Button as TextualButton


class CustomButton(TextualButton):
    """Custom button widget with standardized styling.

    Wraps Textual's Button with consistent styling across the application.
    Supports semantic variants for different button purposes.

    CSS Classes: widget-custom-button

    Variants:
        - default: Standard button styling
        - primary: Primary action button
        - success: Success/action confirmation
        - warning: Caution/warning actions
        - error: Destructive or error actions

    Example:
        >>> button = CustomButton("Submit", variant="primary")
        >>> yield button
    """

    DEFAULT_CSS = """
    CustomButton {
        width: auto;
        min-width: 10;
        height: 3;
        min-height: 3;
        padding: 0 1;
        background: $surface-lighten-1 35%;
        border: none;
        color: $text;
        text-style: none;
        outline: none;
        tint: transparent;
        background-tint: transparent;

        &.-style-default,
        &.-style-flat,
        &.--primary,
        &.--success,
        &.--warning,
        &.--error {
            background: $surface-lighten-1 35%;
            border: none;
            color: $text;
            text-style: none;
            tint: transparent;
            background-tint: transparent;
        }

        &:focus,
        &.-style-default:focus,
        &.-style-flat:focus,
        &.--primary:focus,
        &.--success:focus,
        &.--warning:focus,
        &.--error:focus {
            background: $surface-lighten-1 35%;
            border: none;
            color: $text;
            text-style: none;
            tint: transparent;
            background-tint: transparent;
        }

        &:hover,
        &.-hover,
        &.-style-default:hover,
        &.-style-default.-hover,
        &.-style-flat:hover,
        &.-style-flat.-hover,
        &.--primary:hover,
        &.--success:hover,
        &.--warning:hover,
        &.--error:hover {
            background: $primary;
            border: none;
            color: $surface-darken-3;
            text-style: none;
            tint: transparent;
            background-tint: transparent;
        }

        &.-active,
        &.-active:focus,
        &.-style-default.-active,
        &.-style-default.-active:focus,
        &.-style-flat.-active,
        &.-style-flat.-active:focus,
        &.--primary.-active,
        &.--success.-active,
        &.--warning.-active,
        &.--error.-active {
            background: $surface-lighten-1 35%;
            border: none;
            color: $text;
            text-style: none;
            tint: transparent;
            background-tint: transparent;
        }

        &:disabled,
        &.-style-default:disabled,
        &.-style-flat:disabled,
        &.--primary:disabled,
        &.--success:disabled,
        &.--warning:disabled,
        &.--error:disabled {
            background: $surface-darken-2;
            border: none;
            color: $text-disabled;
            text-style: none;
            tint: transparent;
            background-tint: transparent;
        }

        &.compact {
            min-width: 8;
        }

        &.btn-loading {
            opacity: 60%;
        }

        &.filter-picker-btn, &.cluster-tab-filter-trigger {
            text-wrap: nowrap;
            text-align: center;
            content-align: center middle;
        }

        &.selection-modal-action-btn {
            min-width: 0;
            height: 3;
            min-height: 3;
        }

        & > .button--label {
            width: 1fr;
            height: 1fr;
            text-wrap: nowrap;
            background: transparent;
            border: none;
            color: $text;
            text-align: center;
            content-align: center middle;
            text-style: none;
        }

        &:focus > .button--label,
        &.-style-default:focus > .button--label,
        &.-style-flat:focus > .button--label {
            background: transparent;
            border: none;
            color: $text;
            text-style: none;
        }

        &:hover > .button--label,
        &.-hover > .button--label,
        &.-style-default:hover > .button--label,
        &.-style-flat:hover > .button--label,
        &.--primary:hover > .button--label,
        &.--success:hover > .button--label,
        &.--warning:hover > .button--label,
        &.--error:hover > .button--label {
            background: transparent;
            border: none;
            color: $surface-darken-3;
            text-style: none;
        }

        &.-active > .button--label,
        &.-active:focus > .button--label,
        &.-style-default.-active > .button--label,
        &.-style-flat.-active > .button--label {
            background: transparent;
            border: none;
            color: $text;
            text-style: none;
        }

        &:disabled > .button--label,
        &.-style-default:disabled > .button--label,
        &.-style-flat:disabled > .button--label {
            background: transparent;
            border: none;
            color: $text-disabled;
            text-style: none;
        }
    }
    """

    class Clicked(Message):
        """Message emitted when the button is clicked.

        Attributes:
            button: The CustomButton that was clicked.
        """

        def __init__(self, button: CustomButton) -> None:
            self.button = button
            super().__init__()

    def __init__(
        self,
        label: str,
        variant: str = "default",
        compact: bool = False,
        id: str | None = None,
        classes: str = "",
        disabled: bool = False,
    ):
        """Initialize the custom button.

        Args:
            label: Button text label.
            variant: Button variant (default, primary, success, warning, error).
            compact: Use compact styling with reduced height.
            id: Widget ID.
            classes: CSS classes.
            disabled: Whether the button is disabled.
        """
        super().__init__(label=label, id=id, classes=classes, disabled=disabled)
        self._variant = variant
        self._compact = compact

        # Add variant and compact classes
        if variant != "default":
            self.add_class(f"--{variant}")
        if compact:
            self.add_class("compact")

    def on_click(self, event: Click) -> None:
        """Handle click events.

        Args:
            event: The click event.
        """
        if not self.disabled:
            self.post_message(self.Clicked(self))
