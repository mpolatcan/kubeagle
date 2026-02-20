"""Tests for CustomDialog widgets."""

from __future__ import annotations

from textual.app import App

from kubeagle.widgets.feedback.custom_dialog import (
    CustomActionDialog,
    CustomConfirmDialog,
    CustomDialogFactory,
    CustomHelpDialog,
    CustomInputDialog,
)


class DialogTestApp(App):
    """Test app for dialog widgets."""

    def compose(self):
        yield CustomConfirmDialog(
            message="Are you sure?",
            title="Confirm",
        )
        yield CustomInputDialog(
            prompt="Enter value:",
            title="Input",
        )
        yield CustomActionDialog(
            title="Choose Action",
            actions=["action1", "action2"],
        )


def test_custom_confirm_dialog_instantiation():
    """Test CustomConfirmDialog instantiation."""
    dialog = CustomConfirmDialog(message="Test message")
    assert dialog is not None
    assert dialog._message == "Test message"
    assert dialog._title == "Confirm"


def test_custom_confirm_dialog_with_callbacks():
    """Test CustomConfirmDialog with callbacks."""
    confirm_called = []
    cancel_called = []

    def on_confirm():
        confirm_called.append(True)

    def on_cancel():
        cancel_called.append(True)

    dialog = CustomConfirmDialog(
        message="Test",
        on_confirm=on_confirm,
        on_cancel=on_cancel,
    )
    assert dialog._on_confirm is on_confirm
    assert dialog._on_cancel is on_cancel


def test_custom_input_dialog_instantiation():
    """Test CustomInputDialog instantiation."""
    dialog = CustomInputDialog(prompt="Enter value:", title="Input Dialog")
    assert dialog is not None
    assert dialog._prompt == "Enter value:"
    assert dialog._title == "Input Dialog"


def test_custom_input_dialog_with_validation():
    """Test CustomInputDialog with validation."""
    def validate(val):
        return len(val) >= 3

    dialog = CustomInputDialog(
        prompt="Enter value:",
        validate=validate,
    )
    assert dialog._validate is validate


def test_custom_action_dialog_instantiation():
    """Test CustomActionDialog instantiation."""
    dialog = CustomActionDialog(
        title="Choose Action",
        actions=["option1", "option2", "option3"],
    )
    assert dialog is not None
    assert dialog._title == "Choose Action"
    assert dialog._actions == ["option1", "option2", "option3"]


def test_custom_action_dialog_with_callbacks():
    """Test CustomActionDialog with callbacks."""
    action_called = []
    cancel_called = []

    def on_action(action):
        action_called.append(action)

    def on_cancel():
        cancel_called.append(True)

    dialog = CustomActionDialog(
        title="Choose",
        actions=["a", "b"],
        on_action=on_action,
        on_cancel=on_cancel,
    )
    assert dialog._on_action is on_action
    assert dialog._on_cancel is on_cancel


def test_custom_help_dialog_instantiation():
    """Test CustomHelpDialog instantiation."""
    dialog = CustomHelpDialog()
    assert dialog is not None


def test_custom_dialog_factory():
    """Test CustomDialogFactory."""
    factory = CustomDialogFactory()

    # Test create_confirm
    confirm = factory.create_confirm(
        message="Confirm?",
        title="Title",
    )
    assert isinstance(confirm, CustomConfirmDialog)

    # Test create_input
    input_dialog = factory.create_input(
        prompt="Enter:",
        title="Input",
    )
    assert isinstance(input_dialog, CustomInputDialog)

    # Test create_action
    action = factory.create_action(
        title="Action",
        actions=["opt1", "opt2"],
    )
    assert isinstance(action, CustomActionDialog)

    # Test create_help
    help_dialog = factory.create_help({"h": "Home"})
    assert hasattr(help_dialog, 'CSS_PATH')


def test_custom_dialog_css_path():
    """Test CSS path is set correctly for dialogs."""
    assert CustomConfirmDialog.CSS_PATH.endswith("css/widgets/custom_dialog.tcss")
    assert CustomInputDialog.CSS_PATH.endswith("css/widgets/custom_dialog.tcss")
    assert CustomActionDialog.CSS_PATH.endswith("css/widgets/custom_dialog.tcss")
    assert CustomHelpDialog.CSS_PATH.endswith("css/widgets/custom_dialog.tcss")
