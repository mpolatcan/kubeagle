"""Regression tests for SettingsScreen action button wiring."""

from __future__ import annotations

import pytest
from textual.app import App
from textual.screen import Screen

from kubeagle.models.state.config_manager import AppSettings
from kubeagle.screens.settings.settings_screen import SettingsScreen
from kubeagle.widgets.feedback.custom_dialog import CustomConfirmDialog


class _SettingsScreenActionHarnessApp(App[None]):
    """Test harness that mounts a single SettingsScreen instance."""

    def __init__(self, mounted_screen: SettingsScreen) -> None:
        super().__init__()
        self._mounted_screen = mounted_screen
        self.settings = AppSettings()

    def on_mount(self) -> None:
        self.push_screen(self._mounted_screen)

    def action_nav_home(self) -> None:
        """No-op navigation action used by Settings tabs in tests."""

    def action_nav_cluster(self) -> None:
        """No-op navigation action used by Settings tabs in tests."""

    def action_nav_charts(self) -> None:
        """No-op navigation action used by Settings tabs in tests."""

    def action_nav_optimizer(self) -> None:
        """No-op navigation action used by Settings tabs in tests."""

    def action_nav_export(self) -> None:
        """No-op navigation action used by Settings tabs in tests."""

    def action_nav_settings(self) -> None:
        """No-op navigation action used by Settings tabs in tests."""


class _SettingsScreenStackHarnessApp(App[None]):
    """Test harness that keeps a previous screen under Settings."""

    def __init__(self, mounted_screen: SettingsScreen) -> None:
        super().__init__()
        self._mounted_screen = mounted_screen
        self.settings = AppSettings()

    def on_mount(self) -> None:
        self.push_screen(Screen())
        self.push_screen(self._mounted_screen)

    def action_nav_home(self) -> None:
        """No-op navigation action used by Settings tabs in tests."""

    def action_nav_cluster(self) -> None:
        """No-op navigation action used by Settings tabs in tests."""

    def action_nav_charts(self) -> None:
        """No-op navigation action used by Settings tabs in tests."""

    def action_nav_optimizer(self) -> None:
        """No-op navigation action used by Settings tabs in tests."""

    def action_nav_export(self) -> None:
        """No-op navigation action used by Settings tabs in tests."""

    def action_nav_settings(self) -> None:
        """No-op navigation action used by Settings tabs in tests."""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_settings_action_buttons_call_mapped_handlers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Save/Cancel/Reset buttons should call their mapped Settings actions once."""
    screen = SettingsScreen()
    app = _SettingsScreenActionHarnessApp(screen)
    calls: list[str] = []

    monkeypatch.setattr(screen, "_save_settings", lambda: calls.append("save"))
    monkeypatch.setattr(screen, "_cancel", lambda: calls.append("cancel"))
    monkeypatch.setattr(screen, "_reset_defaults", lambda: calls.append("reset"))

    async with app.run_test(size=(160, 44)) as pilot:
        await pilot.pause(0.2)
        await pilot.click("#save-btn")
        await pilot.click("#cancel-btn")
        await pilot.click("#reset-btn")
        await pilot.pause(0.1)

    assert calls == ["save", "cancel", "reset"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_settings_reset_button_opens_confirmation_dialog() -> None:
    """Reset Defaults should open a confirmation modal."""
    screen = SettingsScreen()
    app = _SettingsScreenActionHarnessApp(screen)

    async with app.run_test(size=(160, 44)) as pilot:
        await pilot.pause(0.2)
        await pilot.click("#reset-btn")
        await pilot.pause(0.1)
        assert isinstance(app.screen, CustomConfirmDialog)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_settings_cancel_confirm_pops_to_previous_screen() -> None:
    """Cancel with dirty state should confirm and then leave Settings."""
    screen = SettingsScreen()
    app = _SettingsScreenStackHarnessApp(screen)

    async with app.run_test(size=(160, 44)) as pilot:
        await pilot.pause(0.2)
        screen._dirty = True  # exercise the confirm-modal cancel flow directly
        await pilot.click("#cancel-btn")
        await pilot.pause(0.1)
        assert isinstance(app.screen, CustomConfirmDialog)
        await pilot.click("#confirm-btn")
        await pilot.pause(0.2)
        assert app.screen is not screen
