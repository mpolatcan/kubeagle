"""CustomProgressBar widget - standardized wrapper around Textual's ProgressBar."""

from __future__ import annotations

from textual.widgets import ProgressBar as TextualProgressBar


class CustomProgressBar(TextualProgressBar):
    """Standardized progress bar with shared styling hooks."""

    CSS_PATH = "../../css/widgets/custom_progress_bar.tcss"

    def __init__(
        self,
        *args,
        classes: str = "",
        **kwargs,
    ) -> None:
        merged_classes = f"widget-custom-progress-bar {classes}".strip()
        super().__init__(*args, classes=merged_classes, **kwargs)
