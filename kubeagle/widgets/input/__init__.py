"""Input widgets for KubEagle TUI.

This module provides input widgets for user interaction:
- CustomCheckbox: Checkbox input widget
- CustomInput: Text input widget
- CustomTextArea: Multi-line text area widget
"""

from kubeagle.widgets.input.custom_checkbox import CustomCheckbox
from kubeagle.widgets.input.custom_input import CustomInput
from kubeagle.widgets.input.custom_text_area import CustomTextArea

__all__ = [
    "CustomCheckbox",
    "CustomInput",
    "CustomTextArea",
]
