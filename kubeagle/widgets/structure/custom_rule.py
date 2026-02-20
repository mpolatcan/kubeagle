"""CustomRule widget - standardized wrapper around Textual's Rule."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.containers import Container
from textual.widgets import Rule as TextualRule

if TYPE_CHECKING:
    from textual.app import ComposeResult


class CustomRule(Container):
    """Standardized rule (horizontal line) wrapper around Textual's Rule widget.

    Provides consistent styling and integration with the TUI design system.
    Wraps Textual's built-in Rule widget with standardized CSS classes.

    CSS Classes: widget-custom-rule

    Example:
        ```python
        CustomRule(
            line_style="solid",
            orientation="horizontal",
            classes="widget-custom-rule"
        )
        ```
    """

    CSS_PATH = "../../css/widgets/custom_rule.tcss"

    def __init__(
        self,
        line_style: str = "solid",
        orientation: str = "horizontal",
        id: str | None = None,
        classes: str = "",
        disabled: bool = False,
    ) -> None:
        """Initialize the custom rule wrapper.

        Args:
            line_style: Line style (solid, dashed, dotted, none).
            orientation: Rule orientation (horizontal, vertical).
            id: Widget ID.
            classes: CSS classes (widget-custom-rule is automatically added).
            disabled: Whether the rule is disabled.
        """
        super().__init__(id=id, classes=f"widget-custom-rule {classes}".strip())
        self._line_style = line_style
        self._orientation = orientation
        self._disabled = disabled
        self._rule: TextualRule | None = None

    def compose(self) -> ComposeResult:
        """Compose the rule with Textual's Rule widget."""
        rule = TextualRule(
            line_style=self._line_style,  # type: ignore[arg-type]
            orientation=self._orientation,  # type: ignore[arg-type]
            id=self.id,
            disabled=self._disabled,
        )
        self._rule = rule
        yield rule

    @property
    def rule(self) -> TextualRule | None:
        """Get the underlying Textual Rule widget.

        Returns:
            The composed Textual Rule widget, or None if not yet composed.
        """
        return self._rule

    @property
    def line_style(self) -> str:
        """Get the line style.

        Returns:
            The line style string.
        """
        if self._rule is None:
            return self._line_style
        return str(self._rule.line_style)

    @line_style.setter
    def line_style(self, val: str) -> None:
        """Set the line style.

        Args:
            val: New line style (solid, dashed, dotted, none).
        """
        self._line_style = val
        if self._rule is not None:
            self._rule.line_style = val  # type: ignore[arg-type]

    @property
    def is_disabled(self) -> bool:
        """Get the disabled state.

        Returns:
            True if disabled, False otherwise.
        """
        if self._rule is None:
            return self._disabled
        return self._rule.disabled

    @is_disabled.setter
    def is_disabled(self, val: bool) -> None:
        """Set the disabled state.

        Args:
            val: New disabled state.
        """
        self._disabled = val
        if self._rule is not None:
            self._rule.disabled = val
