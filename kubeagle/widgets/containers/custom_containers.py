"""CustomContainer widget - standardized wrapper around Textual's Container."""

from __future__ import annotations

from textual.containers import Container as TextualContainer


class CustomContainer(TextualContainer):
    """Standardized wrapper around Textual's Container widget.

    Provides consistent styling and integration with the TUI design system.
    Inherits all functionality from Textual's Container.
    """

    DEFAULT_CSS = """
    CustomContainer {
        height: auto;
        width: 100%;
    }
    """

    def __init__(self, *children, classes: str = "", **kwargs) -> None:
        merged_classes = f"widget-custom-container {classes}".strip()
        super().__init__(*children, classes=merged_classes, **kwargs)


class CustomHorizontal(TextualContainer):
    """Horizontal container that arranges child widgets in a row.

    Provides consistent styling and integration with the TUI design system.
    """

    DEFAULT_CSS = """
    CustomHorizontal {
        layout: horizontal;
        height: auto;
        width: 100%;
    }
    """

    def __init__(self, *children, classes: str = "", **kwargs) -> None:
        merged_classes = f"widget-custom-horizontal {classes}".strip()
        super().__init__(*children, classes=merged_classes, **kwargs)


class CustomVertical(TextualContainer):
    """Vertical container that arranges child widgets in a column.

    Provides consistent styling and integration with the TUI design system.
    """

    DEFAULT_CSS = """
    CustomVertical {
        layout: vertical;
        height: auto;
        width: 100%;
    }
    """

    def __init__(self, *children, classes: str = "", **kwargs) -> None:
        merged_classes = f"widget-custom-vertical {classes}".strip()
        super().__init__(*children, classes=merged_classes, **kwargs)
