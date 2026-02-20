"""CustomFooter widget - standardized wrapper around Textual's Footer."""

from __future__ import annotations

from textual.widgets import Footer as TextualFooter


class CustomFooter(TextualFooter):
    """Standardized footer wrapper around Textual's Footer.

    Provides consistent styling and explicit binding display for the TUI design system.

    Note: DEFAULT_CSS is used for self-targeting rules because SCOPED_CSS
    (True by default) prevents CSS_PATH rules from applying to the widget itself.
    """

    CSS_PATH = "../../css/widgets/custom_footer.tcss"

    DEFAULT_CSS = """
    CustomFooter {
        dock: bottom;
        height: 1;
        min-height: 1;
        max-height: 1;
        background: $footer-background;
        color: $footer-foreground;
        padding: 0;
        overflow-x: hidden;
        overflow-y: hidden;
        scrollbar-size-horizontal: 0;
        scrollbar-size-vertical: 0;
    }
    """

    def __init__(
        self,
        *children,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
        show_command_palette: bool = False,
        compact: bool = True,
    ) -> None:
        # Keep footer dense by default and hide command palette hint to avoid
        # overflow/truncation artifacts on narrow terminal widths.
        normalized_classes = (
            f"widget-custom-footer {classes}".strip()
            if classes
            else "widget-custom-footer"
        )
        super().__init__(
            *children,
            name=name,
            id=id,
            classes=normalized_classes,
            disabled=disabled,
            show_command_palette=show_command_palette,
            compact=compact,
        )

    def on_mount(self) -> None:
        super().on_mount()
        self.styles.layer = "overlay"
        self.styles.height = 1
        self.styles.min_height = 1
        self.styles.max_height = 1
        self.styles.overflow_x = "hidden"
        self.styles.overflow_y = "hidden"

    @property
    def CSS(self) -> str:
        """Return the CSS content as a string for test compatibility."""
        return self.DEFAULT_CSS

__all__ = ["CustomFooter"]
