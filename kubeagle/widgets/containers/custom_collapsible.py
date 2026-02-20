"""CustomCollapsible widget - standardized wrapper around Textual's Collapsible."""

from __future__ import annotations

from textual.widgets import Collapsible as TextualCollapsible


class CustomCollapsible(TextualCollapsible):
    """Standardized collapsible container with shared styling hooks."""

    CSS_PATH = "../../css/widgets/custom_collapsible.tcss"

    def __init__(
        self,
        *args,
        classes: str = "",
        **kwargs,
    ) -> None:
        merged_classes = f"widget-custom-collapsible {classes}".strip()
        super().__init__(*args, classes=merged_classes, **kwargs)
