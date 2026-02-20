"""Configuration manager."""

import json
import os
from pathlib import Path

from pydantic import ValidationError

from kubeagle.models.state.app_settings import (
    AppSettings,
    ConfigError,
    ConfigLoadError,
    ConfigSaveError,
)


class ConfigManager:
    """Manages persistent application settings."""

    SETTINGS_FILENAME = "settings.json"
    APP_NAME = "eks-helm-exporter"

    @classmethod
    def get_config_dir(cls) -> Path:
        """Get the XDG-compliant configuration directory.

        Returns:
            Path to the configuration directory.

        Raises:
            ConfigError: If home directory cannot be determined.
        """
        xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config_home:
            config_dir = Path(xdg_config_home)
        else:
            try:
                config_dir = Path.home() / ".config"
            except RuntimeError as e:
                msg = f"Unable to determine home directory: {e}"
                raise ConfigError(msg) from e

        return config_dir / cls.APP_NAME

    @classmethod
    def get_config_path(cls) -> Path:
        """Get the full path to the settings file.

        Returns:
            Path to the settings JSON file.
        """
        return cls.get_config_dir() / cls.SETTINGS_FILENAME

    @classmethod
    def _ensure_config_dir(cls) -> None:
        """Ensure the configuration directory exists.

        Raises:
            ConfigSaveError: If the directory cannot be created.
        """
        config_dir = cls.get_config_dir()
        try:
            config_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            msg = f"Failed to create configuration directory: {config_dir}"
            raise ConfigSaveError(msg) from e

    @classmethod
    def load(cls) -> AppSettings:
        """Load settings from the configuration file.

        Returns:
            AppSettings instance with loaded configuration.

        Raises:
            ConfigLoadError: If settings fail to load.
        """
        config_path = cls.get_config_path()

        if not config_path.exists():
            # Return default settings if no config file exists
            return AppSettings()

        try:
            with open(config_path, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            msg = f"Invalid JSON in configuration file: {config_path}"
            raise ConfigLoadError(msg) from e
        except OSError as e:
            msg = f"Failed to read configuration file: {config_path}"
            raise ConfigLoadError(msg) from e

        try:
            return AppSettings(**data)
        except ValidationError as e:
            msg = f"Invalid settings in configuration file: {e}"
            raise ConfigLoadError(msg) from e

    @classmethod
    def save(cls, settings: AppSettings) -> None:
        """Save settings to the configuration file.

        Args:
            settings: AppSettings instance to save.

        Raises:
            ConfigSaveError: If settings fail to save.
        """
        cls._ensure_config_dir()
        config_path = cls.get_config_path()

        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(
                    settings.model_dump(mode="json"),
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
        except OSError as e:
            msg = f"Failed to write configuration file: {config_path}"
            raise ConfigSaveError(msg) from e

    @classmethod
    def reset(cls) -> AppSettings:
        """Reset settings to defaults and save.

        Returns:
            AppSettings instance with default configuration.
        """
        settings = AppSettings()
        cls.save(settings)
        return settings
