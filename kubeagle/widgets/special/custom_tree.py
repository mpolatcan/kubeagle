"""CustomTree widget - standardized wrapper around Textual's Tree."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual.containers import Container
from textual.message import Message
from textual.widgets import Tree as TextualTree

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.widgets.tree import TreeNode


class CustomTree(Container):
    """Standardized tree wrapper around Textual's Tree widget.

    Provides consistent styling and integration with the TUI design system.
    Displays hierarchical data with expandable/collapsible nodes.

    CSS Classes: widget-custom-tree

    Example:
        ```python
        tree = CustomTree(label="File System", id="tree-widget")
        tree.root.add("Documents")
        ```
    """

    class NodeSelected(Message):
        """Message emitted when a tree node is selected.

        Attributes:
            tree: The CustomTree that emitted the message.
            node: The selected TreeNode.
        """

        def __init__(self, tree: CustomTree, node: TreeNode[Any]) -> None:
            self.tree = tree
            self.node = node
            super().__init__()

    CSS_PATH = "../../css/widgets/custom_tree.tcss"

    def __init__(
        self,
        label: str = "",
        *,
        id: str | None = None,
        classes: str = "",
        disabled: bool = False,
    ) -> None:
        """Initialize the custom tree wrapper.

        Args:
            label: Label for the tree root.
            id: Widget ID.
            classes: CSS classes (widget-custom-tree is automatically added).
            disabled: Whether the tree is disabled.
        """
        super().__init__(id=id, classes=f"widget-custom-tree {classes}".strip())
        self._label = label
        self._disabled = disabled
        self._tree: TextualTree | None = None

    def compose(self) -> ComposeResult:
        """Compose the tree with Textual's Tree widget."""
        tree = TextualTree(
            label=self._label,
            disabled=self._disabled,
            id=self.id,
        )
        self._tree = tree
        yield tree

    @property
    def tree(self) -> TextualTree:
        """Get the underlying Textual Tree widget.

        Returns:
            The composed Textual Tree widget.
        """
        return self._tree  # type: ignore[return-value]

    @property
    def root(self) -> TreeNode[Any]:
        """Get the root node of the tree.

        Returns:
            The root TreeNode.
        """
        return self.tree.root

    def add(
        self,
        label: str,
        parent: TreeNode[Any] | None = None,
        expand: bool = True,
    ) -> TreeNode[Any]:
        """Add a child node to the tree.

        Args:
            label: Label for the new node.
            parent: Parent node (defaults to root).
            expand: Whether to expand the node.

        Returns:
            The created TreeNode.
        """
        target = parent if parent is not None else self.root
        return target.add(label, expand=expand)

    def add_leaf(
        self,
        label: str,
        parent: TreeNode[Any] | None = None,
    ) -> TreeNode[Any]:
        """Add a leaf node (non-expandable) to the tree.

        Args:
            label: Label for the leaf node.
            parent: Parent node (defaults to root).

        Returns:
            The created TreeNode.
        """
        target = parent if parent is not None else self.root
        return target.add_leaf(label)

    def reset(self, label: str = "") -> None:
        """Reset the tree with a new label.

        Args:
            label: New label for the root node.
        """
        self.tree.reset(label or self._label)

    def _on_tree_node_selected(self, event: TextualTree.NodeSelected) -> None:
        """Handle tree node selection and emit custom NodeSelected message."""
        event.stop()
        self.post_message(self.NodeSelected(self, event.node))
