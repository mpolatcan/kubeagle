"""CustomSelect widget - standardized wrapper around Textual's Select."""

from __future__ import annotations

from typing import TypeVar

from textual.widgets import Select as TextualSelect

SelectType = TypeVar("SelectType")


class CustomSelect(TextualSelect[SelectType]):
    """Standardized select widget with shared styling hooks."""

    CSS_PATH = "css/widgets/custom_select.tcss"

    def __init__(
        self,
        *args,
        classes: str = "",
        **kwargs,
    ) -> None:
        merged_classes = f"widget-custom-select {classes}".strip()
        super().__init__(*args, classes=merged_classes, **kwargs)
