"""CustomSearchBar widget for filter functionality.

Standard Reactive Pattern:
- Inherits from BaseWidget (simple input widget)
- Uses value reactive for input changes

CSS Classes: widget-custom-search-bar
"""

from collections.abc import Callable

from textual.app import ComposeResult
from textual.events import Click
from textual.reactive import reactive
from textual.widgets import Input, Static

from kubeagle.widgets._base import BaseWidget
from kubeagle.widgets.feedback.custom_button import CustomButton


class CustomSearchBar(BaseWidget):
    """Text input field with clear button for search functionality.

    CSS Classes: widget-custom-search-bar
    """

    CSS_PATH = "../../css/widgets/custom_search_bar.tcss"
    _id_pattern = "custom-search-bar-{uuid}"
    _default_classes = "widget-custom-search-bar"

    # Widget-specific reactive for input value
    value = reactive("", init=False)

    def __init__(
        self,
        placeholder: str = "Search...",
        on_change: Callable[[str], None] | None = None,
        id: str | None = None,
        classes: str = "",
    ) -> None:
        """Initialize the custom search bar.

        Args:
            placeholder: Placeholder text for the input.
            on_change: Callback when text changes.
            id: Widget ID.
            classes: CSS classes.
        """
        super().__init__(id=id, classes=classes)
        self._placeholder = placeholder
        self._on_change = on_change

    def compose(self) -> ComposeResult:
        """Compose the search bar widgets."""
        yield Input(
            placeholder=self._placeholder,
            id="search-input",
            classes="search-input",
        )
        yield CustomButton("x", id="clear-btn", classes="clear-btn")

    def on_mount(self) -> None:
        """Connect input change handler."""
        input_widget = self.query_one("#search-input", Input)
        input_widget.focus()

    def watch_value(self, new_value: str) -> None:
        """Handle value changes using reactive pattern.

        Args:
            new_value: The new input value.
        """
        if self._on_change:
            self._on_change(new_value)

    def clear(self) -> None:
        """Clear the search input."""
        input_widget = self.query_one("#search-input", Input)
        input_widget.value = ""
        self.value = ""


class CustomFilterButton(BaseWidget):
    """Simple button widget for filter actions.

    CSS Classes: widget-custom-filter-button
    """

    CSS_PATH = "../../css/widgets/custom_search_bar.tcss"
    _id_pattern = "custom-filter-button-{uuid}"
    _default_classes = "widget-custom-filter-button"

    def __init__(
        self,
        label: str,
        on_click: Callable[[], None] | None = None,
        id: str | None = None,
        classes: str = "",
    ) -> None:
        """Initialize the filter button.

        Args:
            label: Button label.
            on_click: Click callback.
            id: Widget ID.
            classes: CSS classes.
        """
        super().__init__(id=id, classes=classes)
        self._label = label
        self._on_click_callback = on_click

    def compose(self) -> ComposeResult:
        """Compose the filter button."""
        yield Static(self._label, classes="button-label")

    def on_click(self, event: Click) -> None:
        """Handle click event."""
        if self._on_click_callback:
            self._on_click_callback()
