"""CustomDirectoryTree widget - standardized wrapper around Textual's DirectoryTree."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from textual.containers import Container
from textual.widgets import DirectoryTree as TextualDirectoryTree

if TYPE_CHECKING:
    from textual.app import ComposeResult


class CustomDirectoryTree(Container):
    """Standardized directory tree wrapper around Textual's DirectoryTree widget.

    Provides consistent styling and integration with the TUI design system.
    Displays a tree view of the file system for navigation.

    CSS Classes: widget-custom-directory-tree

    Example:
        ```python
        dir_tree = CustomDirectoryTree(
            path=Path("/home/user"),
            id="file-browser"
        )
        ```
    """

    CSS_PATH = "../../css/widgets/custom_directory_tree.tcss"

    def __init__(
        self,
        path: Path | str = Path("."),
        *,
        id: str | None = None,
        classes: str = "",
        disabled: bool = False,
    ) -> None:
        """Initialize the custom directory tree wrapper.

        Args:
            path: Root directory path to display.
            id: Widget ID.
            classes: CSS classes (widget-custom-directory-tree is automatically added).
            disabled: Whether the tree is disabled.
        """
        super().__init__(id=id, classes=f"widget-custom-directory-tree {classes}".strip())
        self._path = Path(path) if isinstance(path, str) else path
        self._disabled = disabled

    def compose(self) -> ComposeResult:
        """Compose the directory tree with Textual's DirectoryTree widget."""
        yield TextualDirectoryTree(
            self._path,
            disabled=self._disabled,
            id=self.id,
        )

    @property
    def directory_tree(self) -> TextualDirectoryTree:
        """Get the underlying Textual DirectoryTree widget.

        Returns:
            The composed Textual DirectoryTree widget.
        """
        return self.query_one(TextualDirectoryTree)

    @property
    def path(self) -> Path | str:
        """Get the current directory path.

        Returns:
            The current Path or str.
        """
        return self.directory_tree.path

    @path.setter
    def path(self, val: Path | str) -> None:
        """Set the directory path.

        Args:
            val: New path.
        """
        path = Path(val) if isinstance(val, str) else val
        self.directory_tree.path = path
