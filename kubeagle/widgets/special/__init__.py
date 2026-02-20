"""Special widgets for KubEagle TUI.

This module provides specialized widgets for various purposes:
- CustomContentSwitcher: Content switching widget
- CustomDirectoryTree: Directory tree navigation
- CustomLink: Hyperlink widget
- CustomTree: Tree data structure display
"""

from kubeagle.widgets.special.custom_content_switcher import (
    CustomContentSwitcher,
)
from kubeagle.widgets.special.custom_directory_tree import (
    CustomDirectoryTree,
)
from kubeagle.widgets.special.custom_link import CustomLink
from kubeagle.widgets.special.custom_tree import CustomTree

__all__ = [
    "CustomContentSwitcher",
    "CustomDirectoryTree",
    "CustomLink",
    "CustomTree",
]
