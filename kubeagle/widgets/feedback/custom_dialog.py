"""Custom dialog widgets for the TUI application.

Standard Reactive Pattern:
- Dialogs are modal screens, inherit from ModalScreen
- No reactive state needed (they manage their own lifecycle)

CSS Classes: widget-custom-dialog
"""

from collections.abc import Callable
from contextlib import suppress

from textual.containers import Horizontal, Vertical
from textual.events import Resize
from textual.screen import ModalScreen
from textual.widgets import Input, Static

from kubeagle.widgets.feedback.custom_button import CustomButton

_DIALOG_MIN_WIDTH = 36
_DIALOG_SIDE_MARGIN = 6
_DIALOG_CONTENT_PADDING = 8
_DIALOG_MIN_HEIGHT = 8
_DIALOG_VERTICAL_MARGIN = 4


def _max_line_width(*values: str) -> int:
    width = 0
    for value in values:
        for line in value.splitlines() or [""]:
            width = max(width, len(line))
    return width


def _fit_dialog_width(dialog: ModalScreen, content_width: int) -> int:
    available_width = max(
        _DIALOG_MIN_WIDTH,
        getattr(dialog.app.size, "width", _DIALOG_MIN_WIDTH + _DIALOG_SIDE_MARGIN)
        - _DIALOG_SIDE_MARGIN,
    )
    return max(
        _DIALOG_MIN_WIDTH,
        min(content_width + _DIALOG_CONTENT_PADDING, available_width),
    )


def _apply_dialog_shell_size(dialog: ModalScreen, content_width: int) -> None:
    dialog_width = _fit_dialog_width(dialog, content_width)
    dialog_max_height = max(
        _DIALOG_MIN_HEIGHT,
        getattr(dialog.app.size, "height", _DIALOG_MIN_HEIGHT + _DIALOG_VERTICAL_MARGIN)
        - _DIALOG_VERTICAL_MARGIN,
    )
    with suppress(Exception):
        container = dialog.query_one(".dialog-container", Vertical)
        width_value = str(dialog_width)
        container.styles.width = width_value
        container.styles.min_width = width_value
        container.styles.max_width = width_value
        container.styles.height = "auto"
        container.styles.max_height = str(dialog_max_height)


class CustomConfirmDialog(ModalScreen[bool]):
    """Confirmation dialog with OK/Cancel buttons."""

    CSS_PATH = "../../css/widgets/custom_dialog.tcss"
    _default_classes = "widget-custom-dialog"

    def __init__(
        self,
        message: str,
        title: str = "Confirm",
        on_confirm: Callable[[], None] | None = None,
        on_cancel: Callable[[], None] | None = None,
    ) -> None:
        """Initialize the custom confirmation dialog.

        Args:
            message: Message to display.
            title: Dialog title.
            on_confirm: Callback when confirmed.
            on_cancel: Callback when cancelled.
        """
        super().__init__()
        self._message = message
        self._title = title
        self._on_confirm = on_confirm
        self._on_cancel = on_cancel

    def compose(self):
        with Vertical(classes="dialog-container"):
            if self._title:
                with Vertical(classes="dialog-title-wrapper"):
                    yield Static(
                        self._title,
                        classes="dialog-title selection-modal-title",
                    )
            yield Static(self._message, classes="dialog-message")
            with Horizontal(classes="dialog-buttons"):
                yield CustomButton(
                    "OK",
                    id="confirm-btn",
                    classes="dialog-btn confirm",
                )
                yield CustomButton(
                    "Cancel",
                    id="cancel-btn",
                    classes="dialog-btn cancel dialog-cancel-btn",
                )

    def on_mount(self) -> None:
        self._apply_dynamic_layout()

    def on_resize(self, _: Resize) -> None:
        self._apply_dynamic_layout()

    def _apply_dynamic_layout(self) -> None:
        content_width = max(
            _max_line_width(self._title, self._message),
            len("OK") + len("Cancel") + 9,
        )
        _apply_dialog_shell_size(self, content_width)

    def on_button_pressed(self, event: CustomButton.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "confirm-btn":
            self.dismiss(True)
            if self._on_confirm:
                self._on_confirm()
        else:
            self.dismiss(False)
            if self._on_cancel:
                self._on_cancel()


class CustomInputDialog(ModalScreen[str]):
    """Dialog with text input."""

    CSS_PATH = "../../css/widgets/custom_dialog.tcss"
    _default_classes = "widget-custom-dialog"

    def __init__(
        self,
        prompt: str,
        title: str = "Input",
        placeholder: str = "",
        default: str = "",
        on_submit: Callable[[str], None] | None = None,
        on_cancel: Callable[[], None] | None = None,
        validate: Callable[[str], bool] | None = None,
    ) -> None:
        """Initialize the custom input dialog.

        Args:
            prompt: Prompt message.
            title: Dialog title.
            placeholder: Input placeholder.
            default: Default value.
            on_submit: Callback when submitted.
            on_cancel: Callback when cancelled.
            validate: Validation function.
        """
        super().__init__()
        self._prompt = prompt
        self._title = title
        self._placeholder = placeholder
        self._default = default
        self._on_submit = on_submit
        self._on_cancel = on_cancel
        self._validate = validate

    def compose(self):
        with Vertical(classes="dialog-container"):
            with Vertical(classes="dialog-title-wrapper"):
                yield Static(
                    self._title,
                    classes="dialog-title selection-modal-title",
                )
            yield Static(self._prompt, classes="dialog-prompt")
            yield Input(
                placeholder=self._placeholder,
                value=self._default,
                id="dialog-input",
                classes="dialog-input",
            )
            with Horizontal(classes="dialog-buttons"):
                yield CustomButton(
                    "Submit",
                    id="submit-btn",
                    classes="dialog-btn submit",
                )
                yield CustomButton(
                    "Cancel",
                    id="cancel-btn",
                    classes="dialog-btn cancel dialog-cancel-btn",
                )

    def on_mount(self) -> None:
        """Focus input on mount."""
        self._apply_dynamic_layout()
        self.query_one("#dialog-input", Input).focus()

    def on_resize(self, _: Resize) -> None:
        self._apply_dynamic_layout()

    def _apply_dynamic_layout(self) -> None:
        content_width = max(
            _max_line_width(
                self._title,
                self._prompt,
                self._placeholder,
                self._default,
            ),
            len("Submit") + len("Cancel") + 9,
        )
        _apply_dialog_shell_size(self, content_width)

    def on_button_pressed(self, event: CustomButton.Pressed) -> None:
        """Handle button presses."""
        input_widget = self.query_one("#dialog-input", Input)

        if event.button.id == "submit-btn":
            value = input_widget.value
            if self._validate and not self._validate(value):
                return
            self.dismiss(value)
            if self._on_submit:
                self._on_submit(value)
        else:
            self.dismiss("")
            if self._on_cancel:
                self._on_cancel()

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        """Handle input submission."""
        input_widget = self.query_one("#dialog-input", Input)
        value = input_widget.value

        if self._validate and not self._validate(value):
            return

        self.dismiss(value)
        if self._on_submit:
            self._on_submit(value)


class CustomActionDialog(ModalScreen[str]):
    """Dialog with custom action buttons."""

    CSS_PATH = "../../css/widgets/custom_dialog.tcss"
    _default_classes = "widget-custom-dialog"

    def __init__(
        self,
        title: str,
        message: str = "",
        actions: list[str] | None = None,
        on_action: Callable[[str], None] | None = None,
        on_cancel: Callable[[], None] | None = None,
    ) -> None:
        """Initialize the custom action dialog.

        Args:
            title: Dialog title.
            message: Message to display.
            actions: List of action labels.
            on_action: Callback when an action is selected.
            on_cancel: Callback when cancelled.
        """
        super().__init__()
        self._title = title
        self._message = message
        self._actions = actions or []
        self._on_action = on_action
        self._on_cancel = on_cancel

    def compose(self):
        with Vertical(classes="dialog-container"):
            with Vertical(classes="dialog-title-wrapper"):
                yield Static(
                    self._title,
                    classes="dialog-title selection-modal-title",
                )
            if self._message:
                yield Static(self._message, classes="dialog-message")
            with Vertical(classes="action-buttons"):
                for action in self._actions:
                    yield CustomButton(
                        action.title(),
                        id=f"action-{action}",
                        classes="dialog-btn action",
                    )
                yield CustomButton(
                    "Cancel",
                    id="cancel-btn",
                    classes="dialog-btn cancel dialog-cancel-btn",
                )

    def on_mount(self) -> None:
        self._apply_dynamic_layout()

    def on_resize(self, _: Resize) -> None:
        self._apply_dynamic_layout()

    def _apply_dynamic_layout(self) -> None:
        action_labels = [action.title() for action in self._actions]
        content_width = max(
            _max_line_width(
                self._title,
                self._message,
                "Cancel",
                *action_labels,
            ),
            20,
        )
        _apply_dialog_shell_size(self, content_width)

    def on_button_pressed(self, event: CustomButton.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "cancel-btn":
            self.dismiss("")
            if self._on_cancel:
                self._on_cancel()
        elif button_id and button_id.startswith("action-"):
            action = button_id[7:]
            self.dismiss(action)
            if self._on_action:
                self._on_action(action)


class CustomHelpDialog(ModalScreen):
    """Help dialog with keyboard shortcuts."""

    CSS_PATH = "../../css/widgets/custom_dialog.tcss"
    _default_classes = "widget-custom-dialog"
    _SHORTCUT_LINES = (
        "h: Home",
        "c: Cluster",
        "C: Charts",
        "o: Optimizer",
        "e: Export",
        "s: Settings (Ctrl+s)",
        "t: Teams",
        "T: Team Statistics",
        "R: Recommendations",
        "?: Help",
        "r: Refresh",
        "q: Quit",
        "Esc: Back / Close",
        "",
        "DataTable: s = Sort",
    )

    def compose(self):
        with Vertical(classes="dialog-container"):
            with Vertical(classes="dialog-title-wrapper"):
                yield Static(
                    "Keyboard Shortcuts",
                    classes="dialog-title selection-modal-title",
                )
            for line in self._SHORTCUT_LINES:
                yield Static(line, classes="shortcut")
            yield CustomButton("Close", id="close-btn", classes="dialog-btn")

    def on_mount(self) -> None:
        self._apply_dynamic_layout()

    def on_resize(self, _: Resize) -> None:
        self._apply_dynamic_layout()

    def _apply_dynamic_layout(self) -> None:
        content_width = max(
            _max_line_width("Keyboard Shortcuts", *self._SHORTCUT_LINES),
            len("Close") + 8,
        )
        _apply_dialog_shell_size(self, content_width)


class CustomDialogFactory:
    """Factory for creating consistent custom dialogs."""

    def create_confirm(
        self,
        message: str,
        title: str = "Confirm",
        on_confirm: Callable[[], None] | None = None,
        on_cancel: Callable[[], None] | None = None,
    ) -> CustomConfirmDialog:
        """Create a confirmation dialog."""
        return CustomConfirmDialog(
            message=message,
            title=title,
            on_confirm=on_confirm,
            on_cancel=on_cancel,
        )

    def create_input(
        self,
        prompt: str,
        title: str = "Input",
        placeholder: str = "",
        default: str = "",
        on_submit: Callable[[str], None] | None = None,
        on_cancel: Callable[[], None] | None = None,
        validate: Callable[[str], bool] | None = None,
    ) -> CustomInputDialog:
        """Create an input dialog."""
        return CustomInputDialog(
            prompt=prompt,
            title=title,
            placeholder=placeholder,
            default=default,
            on_submit=on_submit,
            on_cancel=on_cancel,
            validate=validate,
        )

    def create_action(
        self,
        title: str,
        message: str = "",
        actions: list[str] | None = None,
        on_action: Callable[[str], None] | None = None,
        on_cancel: Callable[[], None] | None = None,
    ) -> CustomActionDialog:
        """Create an action selection dialog."""
        return CustomActionDialog(
            title=title,
            message=message,
            actions=actions,
            on_action=on_action,
            on_cancel=on_cancel,
        )

    def create_help(self, shortcuts: dict[str, str]) -> ModalScreen:
        """Create a help dialog from a shortcuts dictionary."""

        class HelpDialog(ModalScreen):
            CSS_PATH = "../../css/widgets/custom_dialog.tcss"

            def __init__(self):
                super().__init__()
                self._shortcuts = shortcuts

            def compose(self):
                with Vertical(classes="dialog-container"):
                    with Vertical(classes="dialog-title-wrapper"):
                        yield Static(
                            "Keyboard Shortcuts",
                            classes="dialog-title selection-modal-title",
                        )
                    for key, description in self._shortcuts.items():
                        yield Static(f"{key}: {description}", classes="shortcut")
                    yield CustomButton("Close", id="close-btn", classes="dialog-btn")

            def on_mount(self) -> None:
                self._apply_dynamic_layout()

            def on_resize(self, _: Resize) -> None:
                self._apply_dynamic_layout()

            def _apply_dynamic_layout(self) -> None:
                content_lines = [f"{key}: {description}" for key, description in self._shortcuts.items()]
                content_width = max(
                    _max_line_width("Keyboard Shortcuts", *content_lines),
                    len("Close") + 8,
                )
                _apply_dialog_shell_size(self, content_width)

        return HelpDialog()
