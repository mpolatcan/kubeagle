"""Widgets module for the KubEagle TUI.

This module provides all reusable widgets organized into submodules:
- containers: Container widgets (CustomCard, CustomCollapsible, CustomContainer)
- data: Data display widgets (tables, KPI, indicators)
- display: Display widgets (CustomDigits, CustomMarkdown, CustomMarkdownViewer, CustomProgressBar, CustomRichLog, CustomStatic)
- feedback: Button, dialogs
- filter: Search and filter widgets
- input: Input widgets (CustomCheckbox, CustomInput, CustomTextArea)
- selection: Selection widgets (CustomOptionList, CustomRadio*, CustomSelect, CustomSelectionList, CustomSwitch)
- special: Specialized widgets (CustomContentSwitcher, CustomDirectoryTree, CustomLink, CustomTree)
- structure: Structure widgets (CustomFooter, CustomHeader, CustomRule)
- tabs: Tab widgets (CustomTab, CustomTabs, CustomTabbedContent, CustomTabPane)
"""

# Base classes
from kubeagle.widgets._base import (
    BaseWidget,
    CompositeWidget,
    StatefulWidget,
)

# Container widgets
from kubeagle.widgets.containers import (
    CustomCard,
    CustomCollapsible,
    CustomContainer,
    CustomHorizontal,
    CustomVertical,
)

# Data display widgets
from kubeagle.widgets.data import (
    CustomChartsTable,
    CustomColumnDef,
    CustomDataTable,
    CustomEventsTable,
    CustomKPI,
    CustomNodeTable,
    CustomStatusIndicator,
    CustomTableBase,
    CustomTableBuilder,
    CustomTableMixin,
    CustomViolationsTable,
)

# Display widgets
from kubeagle.widgets.display import (
    CustomDigits,
    CustomMarkdown,
    CustomMarkdownViewer,
    CustomProgressBar,
    CustomRichLog,
    CustomStatic,
)

# Feedback widgets
from kubeagle.widgets.feedback import (
    CustomActionDialog,
    CustomButton,
    CustomConfirmDialog,
    CustomDialogFactory,
    CustomHelpDialog,
    CustomInputDialog,
    CustomLoadingIndicator,
)

# Filter widgets
from kubeagle.widgets.filter import (
    CustomFilterBar,
    CustomFilterButton,
    CustomFilterChip,
    CustomFilterGroup,
    CustomSearchBar,
)

# Input widgets
from kubeagle.widgets.input import (
    CustomCheckbox,
    CustomInput,
    CustomTextArea,
)

# Selection widgets
from kubeagle.widgets.selection import (
    CustomOptionList,
    CustomRadioButton,
    CustomRadioSet,
    CustomSelect,
    CustomSelectionList,
    CustomSwitch,
)

# Special widgets
from kubeagle.widgets.special import (
    CustomContentSwitcher,
    CustomDirectoryTree,
    CustomLink,
    CustomTree,
)

# Structure widgets
from kubeagle.widgets.structure import (
    CustomFooter,
    CustomHeader,
    CustomRule,
)

# Tab widgets
from kubeagle.widgets.tabs import (
    CustomTab,
    CustomTabbedContent,
    CustomTabPane,
    CustomTabs,
)

__all__ = [
    # Base classes
    "BaseWidget",
    "CompositeWidget",
    "StatefulWidget",
    # Structure
    "CustomHeader",
    "CustomFooter",
    "CustomRule",
    # Containers
    "CustomCard",
    "CustomCollapsible",
    "CustomContainer",
    "CustomHorizontal",
    "CustomVertical",
    # Input
    "CustomInput",
    "CustomCheckbox",
    "CustomTextArea",
    # Selection
    "CustomRadioButton",
    "CustomRadioSet",
    "CustomSelect",
    "CustomSelectionList",
    "CustomOptionList",
    "CustomSwitch",
    # Display
    "CustomStatic",
    "CustomDigits",
    "CustomMarkdown",
    "CustomMarkdownViewer",
    "CustomProgressBar",
    "CustomRichLog",
    # Special
    "CustomContentSwitcher",
    "CustomLink",
    "CustomTree",
    "CustomDirectoryTree",
    # Tabs
    "CustomTab",
    "CustomTabs",
    "CustomTabbedContent",
    "CustomTabPane",
    # Feedback
    "CustomButton",
    "CustomLoadingIndicator",
    "CustomConfirmDialog",
    "CustomInputDialog",
    "CustomActionDialog",
    "CustomHelpDialog",
    "CustomDialogFactory",
    # Filter
    "CustomSearchBar",
    "CustomFilterChip",
    "CustomFilterGroup",
    "CustomFilterBar",
    "CustomFilterButton",
    # Data tables
    "CustomTableBase",
    "CustomTableMixin",
    "CustomDataTable",
    "CustomNodeTable",
    "CustomChartsTable",
    "CustomEventsTable",
    "CustomViolationsTable",
    "CustomColumnDef",
    "CustomTableBuilder",
    # KPI and indicators
    "CustomKPI",
    "CustomStatusIndicator",
]
