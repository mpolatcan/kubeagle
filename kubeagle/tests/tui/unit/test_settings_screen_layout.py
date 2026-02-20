"""Regression tests for SettingsScreen responsive layout behavior."""

from __future__ import annotations

import pytest
from textual.app import App

from kubeagle.models.state.config_manager import AppSettings
from kubeagle.screens.settings.settings_screen import SettingsScreen
from kubeagle.widgets.containers import CustomContainer


class _SettingsScreenHarnessApp(App[None]):
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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_settings_screen_mount_applies_wide_layout_classes() -> None:
    """Settings should open with two-column layout on wide terminals."""
    screen = SettingsScreen()
    app = _SettingsScreenHarnessApp(screen)

    async with app.run_test(size=(160, 44)) as pilot:
        await pilot.pause(0.2)
        sections = screen.query_one("#settings-sections", CustomContainer)
        assert "-two-column" in sections.classes
        assert "-single-column" not in sections.classes


@pytest.mark.unit
@pytest.mark.asyncio
async def test_settings_screen_resume_reapplies_responsive_layout_classes() -> None:
    """Returning to Settings should re-sync responsive layout classes."""
    screen = SettingsScreen()
    app = _SettingsScreenHarnessApp(screen)

    async with app.run_test(size=(160, 44)) as pilot:
        await pilot.pause(0.2)

        sections = screen.query_one("#settings-sections", CustomContainer)
        sections.remove_class("-single-column", "-two-column")
        sections.add_class("-single-column")

        screen.on_screen_resume()
        await pilot.pause(0.2)

        assert "-two-column" in sections.classes
        assert "-single-column" not in sections.classes
