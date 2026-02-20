"""Widget configuration utilities and settings.

This module provides configuration management for widgets including:
- Widget ID pattern templates
- CSS class name generators
- Theme-aware styling constants
- Widget registry for tracking widget instances

Example:
    >>> from kubeagle.widgets._config import WidgetConfig
    >>>
    >>> config = WidgetConfig()
    >>> card_id = config.generate_id("kpi", title="stats")
    >>> classes = config.compose_classes("card", "highlighted", "dark")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from kubeagle.constants.enums import WidgetCategory


@dataclass
class WidgetConfig:
    """Configuration management for widget creation and styling.

    Provides utilities for:
    - Generating consistent widget IDs
    - Composing CSS class names
    - Managing widget categories
    - Theme-aware styling
    """

    # ID pattern templates
    ID_PATTERNS: ClassVar[dict[str, str]] = {
        "kpi": "kpi-{title}-{uuid}",
        "card": "card-{name}-{uuid}",
        "button": "btn-{name}-{uuid}",
        "input": "input-{name}-{uuid}",
        "dialog": "dialog-{name}-{uuid}",
        "table": "table-{name}-{uuid}",
        "filter": "filter-{name}-{uuid}",
        "toast": "toast-{name}-{uuid}",
        "spinner": "spinner-{name}-{uuid}",
        "progress": "progress-{name}-{uuid}",
    }

    # Standard CSS class prefixes
    CLASS_PREFIXES: ClassVar[dict[str, str]] = {
        "widget": "widget",
        "container": "container",
        "interactive": "interactive",
        "loading": "loading",
        "error": "error",
        "success": "success",
        "warning": "warning",
        "muted": "muted",
        "accent": "accent",
        "primary": "primary",
        "secondary": "secondary",
    }

    # Theme color mappings
    THEME_COLORS: ClassVar[dict[str, str]] = {
        "success": "$success",
        "error": "$error",
        "warning": "$warning",
        "info": "$accent",
        "muted": "$text-muted",
        "primary": "$primary",
        "secondary": "$secondary",
    }

    def generate_id(self, pattern_name: str, **kwargs: str) -> str:
        """Generate a widget ID using a named pattern.

        Args:
            pattern_name: Name of the pattern to use.
            **kwargs: Values for pattern placeholders.

        Returns:
            Generated ID string.
        """
        import uuid

        pattern = self.ID_PATTERNS.get(pattern_name, "widget-{name}-{uuid}")
        short_uuid = uuid.uuid4().hex[:8]

        # Build context for pattern substitution
        context = {
            "title": kwargs.get("title", "").lower().replace(" ", "-"),
            "name": kwargs.get("name", "").lower().replace(" ", "-"),
            "uuid": short_uuid,
            **kwargs,
        }

        return pattern.format(**context)

    def compose_classes(self, *class_names: str, prefix: str | None = None) -> str:
        """Compose CSS class names into a single string.

        Args:
            *class_names: CSS class names to include.
            prefix: Optional prefix to add to all classes.

        Returns:
            Space-separated class string.
        """
        result = [f"{prefix}-{name}" if prefix else name for name in class_names if name]
        return " ".join(result)

    def status_class(self, status: str) -> str:
        """Get CSS class for a status value.

        Args:
            status: Status string (success, error, warning, etc.)

        Returns:
            Corresponding CSS class name.
        """
        return f"status-{status.lower()}"

    def severity_class(self, severity: str) -> str:
        """Get CSS class for a severity level.

        Args:
            severity: Severity string (critical, high, medium, low)

        Returns:
            Corresponding CSS class name.
        """
        return f"severity-{severity.lower()}"


@dataclass
class WidgetRegistry:
    """Registry for tracking widget instances and their configurations.

    Useful for debugging, testing, and managing widget lifecycle.

    Attributes:
        _instances: Dictionary mapping widget IDs to instances.
    """

    _instances: dict[str, object] = field(default_factory=dict)
    _configs: dict[str, dict] = field(default_factory=dict)

    def register(self, widget_id: str, instance: object, config: dict | None = None) -> None:
        """Register a widget instance.

        Args:
            widget_id: Unique identifier for the widget.
            instance: The widget instance.
            config: Optional configuration dictionary.
        """
        self._instances[widget_id] = instance
        if config:
            self._configs[widget_id] = config

    def get(self, widget_id: str) -> object | None:
        """Get a widget by ID.

        Args:
            widget_id: The widget ID to find.

        Returns:
            The widget instance or None.
        """
        return self._instances.get(widget_id)

    def unregister(self, widget_id: str) -> None:
        """Remove a widget from the registry.

        Args:
            widget_id: The widget ID to remove.
        """
        self._instances.pop(widget_id, None)
        self._configs.pop(widget_id, None)

    def list_by_category(self, category: WidgetCategory) -> list[str]:
        """List widget IDs by category.

        Args:
            category: The category to filter by.

        Returns:
            List of widget IDs in the category.
        """
        # This is a placeholder - actual implementation would track categories
        return list(self._instances.keys())


# Global configuration instance
WIDGET_CONFIG = WidgetConfig()
WIDGET_REGISTRY = WidgetRegistry()
