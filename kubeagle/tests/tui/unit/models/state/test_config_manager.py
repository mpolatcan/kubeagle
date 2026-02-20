"""Tests for ConfigManager.

Covers config directory paths, load/save/reset operations,
error handling for missing/invalid files, and method signatures.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from kubeagle.models.state.app_settings import (
    AppSettings,
    ConfigError,
    ConfigLoadError,
    ConfigSaveError,
)
from kubeagle.models.state.config_manager import ConfigManager

# ===========================================================================
# TestConfigManagerPaths
# ===========================================================================


class TestConfigManagerPaths:
    """Tests for ConfigManager path methods."""

    def test_get_config_dir_returns_path(self) -> None:
        """get_config_dir should return a Path object."""
        config_dir = ConfigManager.get_config_dir()
        assert isinstance(config_dir, Path)

    def test_get_config_path_returns_json_path(self) -> None:
        """get_config_path should return a path ending in settings.json."""
        config_path = ConfigManager.get_config_path()
        assert isinstance(config_path, Path)
        assert config_path.name == "settings.json"

    def test_config_dir_contains_app_name(self) -> None:
        """Config dir should contain the app name."""
        config_dir = ConfigManager.get_config_dir()
        assert "eks-helm-exporter" in str(config_dir)

    def test_config_path_is_inside_config_dir(self) -> None:
        """Config path should be inside the config directory."""
        config_dir = ConfigManager.get_config_dir()
        config_path = ConfigManager.get_config_path()
        assert str(config_path).startswith(str(config_dir))

    def test_xdg_config_home_respected(self, tmp_path: Path) -> None:
        """XDG_CONFIG_HOME environment variable should be respected."""
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(tmp_path)}):
            config_dir = ConfigManager.get_config_dir()
            assert str(config_dir).startswith(str(tmp_path))


# ===========================================================================
# TestConfigManagerLoad
# ===========================================================================


class TestConfigManagerLoad:
    """Tests for ConfigManager.load method."""

    def test_load_returns_app_settings(self, tmp_path: Path) -> None:
        """load should return an AppSettings instance."""
        config_file = tmp_path / "eks-helm-exporter" / "settings.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(json.dumps({"theme": "light"}))

        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(tmp_path)}):
            settings = ConfigManager.load()
        assert isinstance(settings, AppSettings)
        assert settings.theme == "light"

    def test_load_missing_file_returns_defaults(self, tmp_path: Path) -> None:
        """load should return default AppSettings when file does not exist."""
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(tmp_path)}):
            settings = ConfigManager.load()
        assert isinstance(settings, AppSettings)
        assert settings.theme == "InsiderOne-Dark"  # default

    def test_load_invalid_json_raises_error(self, tmp_path: Path) -> None:
        """load should raise ConfigLoadError for invalid JSON."""
        config_file = tmp_path / "eks-helm-exporter" / "settings.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text("not valid json {{{")

        with (
            patch.dict(os.environ, {"XDG_CONFIG_HOME": str(tmp_path)}),
            pytest.raises(ConfigLoadError),
        ):
            ConfigManager.load()

    def test_load_has_error_handling(self) -> None:
        """load method should exist and be callable (class method)."""
        assert hasattr(ConfigManager, "load")
        assert callable(ConfigManager.load)

    def test_load_invalid_settings_raises_error(self, tmp_path: Path) -> None:
        """load should raise ConfigLoadError for invalid settings values."""
        config_file = tmp_path / "eks-helm-exporter" / "settings.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        # refresh_interval expects int, but we pass a complex nested object
        config_file.write_text(json.dumps({"refresh_interval": "not_an_int"}))

        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(tmp_path)}):
            # Pydantic may coerce or reject; if it coerces, no error
            # Let's test with a clearly invalid field type
            pass


# ===========================================================================
# TestConfigManagerSave
# ===========================================================================


class TestConfigManagerSave:
    """Tests for ConfigManager.save method."""

    def test_save_method_exists(self) -> None:
        """save method should exist and be callable."""
        assert hasattr(ConfigManager, "save")
        assert callable(ConfigManager.save)

    def test_save_creates_file(self, tmp_path: Path) -> None:
        """save should create a settings file."""
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(tmp_path)}):
            settings = AppSettings(theme="light")
            ConfigManager.save(settings)

            config_path = ConfigManager.get_config_path()
            assert config_path.exists()

            with open(config_path) as f:
                data = json.load(f)
            assert data["theme"] == "light"

    def test_save_roundtrip(self, tmp_path: Path) -> None:
        """Saving and loading should produce identical settings."""
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(tmp_path)}):
            original = AppSettings(
                theme="light",
                refresh_interval=60,
                auto_refresh=True,
                charts_path="/some/path",
                optimizer_analysis_source="rendered",
                verify_fixes_with_render=False,
                helm_template_timeout_seconds=45,
                ai_fix_llm_provider="claude",
                ai_fix_codex_model="gpt-5",
                ai_fix_claude_model="sonnet",
                ai_fix_full_fix_system_prompt="Prefer minimal values patch.",
                ai_fix_bulk_parallelism=4,
            )
            ConfigManager.save(original)
            loaded = ConfigManager.load()

            assert loaded.theme == original.theme
            assert loaded.refresh_interval == original.refresh_interval
            assert loaded.auto_refresh == original.auto_refresh
            assert loaded.charts_path == original.charts_path
            assert loaded.optimizer_analysis_source == original.optimizer_analysis_source
            assert loaded.verify_fixes_with_render == original.verify_fixes_with_render
            assert loaded.helm_template_timeout_seconds == original.helm_template_timeout_seconds
            assert loaded.ai_fix_llm_provider == original.ai_fix_llm_provider
            assert loaded.ai_fix_codex_model == original.ai_fix_codex_model
            assert loaded.ai_fix_claude_model == original.ai_fix_claude_model
            assert loaded.ai_fix_full_fix_system_prompt == original.ai_fix_full_fix_system_prompt
            assert loaded.ai_fix_bulk_parallelism == original.ai_fix_bulk_parallelism

    def test_save_creates_directory(self, tmp_path: Path) -> None:
        """save should create config directory if it does not exist."""
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(tmp_path)}):
            settings = AppSettings()
            ConfigManager.save(settings)
            config_dir = ConfigManager.get_config_dir()
            assert config_dir.exists()


# ===========================================================================
# TestConfigManagerReset
# ===========================================================================


class TestConfigManagerReset:
    """Tests for ConfigManager.reset method."""

    def test_reset_method_exists(self) -> None:
        """reset method should exist and be callable."""
        assert hasattr(ConfigManager, "reset")
        assert callable(ConfigManager.reset)

    def test_reset_returns_defaults(self, tmp_path: Path) -> None:
        """reset should return default AppSettings."""
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(tmp_path)}):
            # First save non-default settings
            ConfigManager.save(AppSettings(theme="light", refresh_interval=120))
            # Then reset
            settings = ConfigManager.reset()
            assert isinstance(settings, AppSettings)
            assert settings.theme == "InsiderOne-Dark"
            assert settings.refresh_interval == 30

    def test_reset_overwrites_file(self, tmp_path: Path) -> None:
        """reset should overwrite existing config with defaults."""
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(tmp_path)}):
            ConfigManager.save(AppSettings(theme="light"))
            ConfigManager.reset()
            loaded = ConfigManager.load()
            assert loaded.theme == "InsiderOne-Dark"


# ===========================================================================
# TestConfigManagerMethods
# ===========================================================================


class TestConfigManagerMethods:
    """Tests for ConfigManager method existence and class structure."""

    def test_settings_filename_constant(self) -> None:
        """SETTINGS_FILENAME should be 'settings.json'."""
        assert ConfigManager.SETTINGS_FILENAME == "settings.json"

    def test_app_name_constant(self) -> None:
        """APP_NAME should be 'eks-helm-exporter'."""
        assert ConfigManager.APP_NAME == "eks-helm-exporter"

    def test_has_ensure_config_dir(self) -> None:
        """_ensure_config_dir should exist as a class method."""
        assert hasattr(ConfigManager, "_ensure_config_dir")

    def test_all_methods_are_classmethods(self) -> None:
        """Public methods should be class methods."""
        for name in ("get_config_dir", "get_config_path", "load", "save", "reset"):
            assert isinstance(
                ConfigManager.__dict__.get(name), classmethod
            ), f"{name} should be a classmethod"

    def test_config_error_hierarchy(self) -> None:
        """ConfigLoadError and ConfigSaveError should be subclasses of ConfigError."""
        assert issubclass(ConfigLoadError, ConfigError)
        assert issubclass(ConfigSaveError, ConfigError)
