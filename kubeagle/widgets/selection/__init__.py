"""Selection widgets for KubEagle TUI.

This module provides selection widgets for choosing options:
- CustomOptionList: Dropdown option list
- CustomRadioButton: Radio button widget
- CustomRadioSet: Radio button group
- CustomSelect: Select dropdown widget
- CustomSelectionList: List with selection support
- CustomSwitch: Toggle switch widget
"""

from kubeagle.widgets.selection.custom_option_list import CustomOptionList
from kubeagle.widgets.selection.custom_radio_button import (
    CustomRadioButton,
)
from kubeagle.widgets.selection.custom_radio_set import CustomRadioSet
from kubeagle.widgets.selection.custom_select import CustomSelect
from kubeagle.widgets.selection.custom_selection_list import (
    CustomSelectionList,
)
from kubeagle.widgets.selection.custom_switch import CustomSwitch

__all__ = [
    "CustomOptionList",
    "CustomRadioButton",
    "CustomRadioSet",
    "CustomSelect",
    "CustomSelectionList",
    "CustomSwitch",
]
