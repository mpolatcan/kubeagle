"""Parse TUI screen files to extract widget definitions.

Uses Python AST to analyze compose() methods and extract:
- Widget types and their IDs
- Widget hierarchy (containers, tabs)
- Text content and labels
- CSS classes
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger


@dataclass(slots=True)
class WidgetInfo:
    """Information about a discovered widget."""

    widget_type: str
    widget_id: str | None = None
    classes: list[str] = field(default_factory=list)
    text_content: str | None = None
    children: list[WidgetInfo] = field(default_factory=list)
    parent_type: str | None = None
    tab_id: str | None = None  # If widget is inside a TabPane


@dataclass(slots=True)
class ScreenInfo:
    """Information about a discovered screen."""

    name: str
    class_name: str
    file_path: Path
    docstring: str | None = None
    css_path: str | None = None
    widgets: list[WidgetInfo] = field(default_factory=list)
    bindings_name: str | None = None  # e.g., "CLUSTER_SCREEN_BINDINGS"


class ScreenParser:
    """Parse screen files to extract widget definitions."""

    # Widget types we care about for visual analysis
    VISUAL_WIDGETS = frozenset([
        "Static",
        "Button",
        "Input",
        "DataTable",
        "ListView",
        "Tree",
        "SelectionList",
        "TabbedContent",
        "TabPane",
        "LoadingIndicator",
        "ProgressBar",
        "Header",
        "Footer",
    ])

    # Container types that may hold visual widgets
    CONTAINER_WIDGETS = frozenset([
        "Container",
        "Horizontal",
        "Vertical",
        "Grid",
        "ScrollableContainer",
        "Center",
    ])

    def __init__(self, screens_path: Path | None = None) -> None:
        """Initialize parser.

        Args:
            screens_path: Path to screens directory. If None, will be detected.
        """
        self.screens_path = screens_path
        self._cache: dict[str, ScreenInfo] = {}

    def find_screens_directory(self) -> Path | None:
        """Find the TUI screens directory.

        Returns:
            Path to screens directory or None if not found.
        """
        if self.screens_path and self.screens_path.exists():
            return self.screens_path

        # Try common locations relative to this file
        current = Path(__file__).parent
        search_paths = [
            current.parent.parent.parent.parent.parent
            / "kubeagle"
            / "screens",
            Path.cwd() / "kubeagle" / "screens",
            Path.cwd().parent / "kubeagle" / "screens",
        ]

        for path in search_paths:
            if path.exists() and path.is_dir():
                self.screens_path = path
                return path

        return None

    def discover_screen_files(self) -> list[Path]:
        """Discover all screen Python files.

        Returns:
            List of paths to screen files.
        """
        screens_dir = self.find_screens_directory()
        if not screens_dir:
            logger.warning("Could not find screens directory")
            return []

        screen_files = []

        # Find all *_screen.py files recursively
        for py_file in screens_dir.rglob("*_screen.py"):
            if not py_file.name.startswith("_"):
                screen_files.append(py_file)

        return sorted(screen_files)

    def parse_screen_file(self, file_path: Path) -> ScreenInfo | None:
        """Parse a single screen file.

        Args:
            file_path: Path to the screen Python file.

        Returns:
            ScreenInfo with extracted data, or None on error.
        """
        cache_key = str(file_path)
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError) as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return None

        # Find Screen subclass
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if it's a Screen subclass
                if self._is_screen_subclass(node):
                    screen_info = self._extract_screen_info(node, file_path)
                    self._cache[cache_key] = screen_info
                    return screen_info

        return None

    def _is_screen_subclass(self, node: ast.ClassDef) -> bool:
        """Check if class is a Screen subclass.

        Args:
            node: AST ClassDef node.

        Returns:
            True if class inherits from Screen.
        """
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == "Screen":
                return True
            if isinstance(base, ast.Attribute) and base.attr == "Screen":
                return True
        return False

    def _extract_screen_info(
        self, class_node: ast.ClassDef, file_path: Path
    ) -> ScreenInfo:
        """Extract screen information from class definition.

        Args:
            class_node: AST ClassDef node.
            file_path: Path to source file.

        Returns:
            ScreenInfo with extracted data.
        """
        # Get docstring
        docstring = ast.get_docstring(class_node)

        # Derive screen name from class name (e.g., ClusterScreen -> cluster)
        class_name = class_node.name
        screen_name = class_name.replace("Screen", "").lower()

        screen_info = ScreenInfo(
            name=screen_name,
            class_name=class_name,
            file_path=file_path,
            docstring=docstring,
        )

        # Extract class attributes
        for item in class_node.body:
            if isinstance(item, ast.Assign):
                self._extract_class_attribute(item, screen_info)
            elif isinstance(item, ast.FunctionDef) and item.name == "compose":
                # Extract widgets from compose method
                screen_info.widgets = self._extract_compose_widgets(item)

        return screen_info

    def _extract_class_attribute(
        self, node: ast.Assign, screen_info: ScreenInfo
    ) -> None:
        """Extract class-level attributes like CSS_PATH, BINDINGS.

        Args:
            node: AST Assign node.
            screen_info: ScreenInfo to update.
        """
        for target in node.targets:
            if isinstance(target, ast.Name):
                if target.id == "CSS_PATH" and isinstance(node.value, ast.Constant):
                    value = node.value.value
                    if isinstance(value, str):
                        screen_info.css_path = value
                elif target.id == "BINDINGS" and isinstance(node.value, ast.Name):
                    screen_info.bindings_name = node.value.id

    def _extract_compose_widgets(
        self, func_node: ast.FunctionDef
    ) -> list[WidgetInfo]:
        """Extract widget information from compose() method.

        Args:
            func_node: AST FunctionDef node for compose().

        Returns:
            List of discovered widgets.
        """
        widgets: list[WidgetInfo] = []
        current_tab: str | None = None

        for node in ast.walk(func_node):
            # Handle yield statements
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Yield):
                yield_value = node.value.value
                if yield_value:
                    widget = self._extract_widget_from_call(yield_value, current_tab)
                    if widget:
                        widgets.append(widget)

            # Handle 'with' statements (for TabbedContent/TabPane)
            elif isinstance(node, ast.With):
                for item in node.items:
                    if isinstance(item.context_expr, ast.Call):
                        call = item.context_expr
                        func_name = self._get_call_name(call)
                        if func_name == "TabPane":
                            # Extract tab ID
                            tab_id = self._extract_keyword_arg(call, "id")
                            if tab_id:
                                current_tab = tab_id

        return widgets

    def _extract_widget_from_call(
        self, node: ast.AST, current_tab: str | None = None
    ) -> WidgetInfo | None:
        """Extract widget info from a Call AST node.

        Args:
            node: AST node (usually a Call).
            current_tab: Current tab context if inside TabPane.

        Returns:
            WidgetInfo or None if not a widget.
        """
        if not isinstance(node, ast.Call):
            return None

        func_name = self._get_call_name(node)
        if not func_name:
            return None

        # Check if it's a widget we care about
        is_visual = func_name in self.VISUAL_WIDGETS
        is_container = func_name in self.CONTAINER_WIDGETS

        if not is_visual and not is_container:
            return None

        widget = WidgetInfo(
            widget_type=func_name,
            tab_id=current_tab,
        )

        # Extract id keyword argument
        widget.widget_id = self._extract_keyword_arg(node, "id")

        # Extract classes keyword argument
        classes_str = self._extract_keyword_arg(node, "classes")
        if classes_str:
            widget.classes = classes_str.split()

        # Extract text content (first positional arg for Static/Button)
        if func_name in ("Static", "Button") and node.args:
            first_arg = node.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(
                first_arg.value, str
            ):
                widget.text_content = first_arg.value

        # Extract placeholder for Input
        if func_name == "Input":
            widget.text_content = self._extract_keyword_arg(node, "placeholder")

        # For containers, extract child widgets
        if is_container:
            for arg in node.args:
                child = self._extract_widget_from_call(arg, current_tab)
                if child:
                    child.parent_type = func_name
                    widget.children.append(child)

        return widget

    def _get_call_name(self, node: ast.Call) -> str | None:
        """Get the function name from a Call node.

        Args:
            node: AST Call node.

        Returns:
            Function name or None.
        """
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr
        return None

    def _extract_keyword_arg(self, node: ast.Call, arg_name: str) -> str | None:
        """Extract a string keyword argument value.

        Args:
            node: AST Call node.
            arg_name: Name of the keyword argument.

        Returns:
            String value or None.
        """
        for kw in node.keywords:
            if kw.arg == arg_name:
                if isinstance(kw.value, ast.Constant) and isinstance(
                    kw.value.value, str
                ):
                    return kw.value.value
        return None

    def parse_all_screens(self) -> dict[str, ScreenInfo]:
        """Parse all discovered screen files.

        Returns:
            Dict mapping screen name to ScreenInfo.
        """
        screens: dict[str, ScreenInfo] = {}

        for file_path in self.discover_screen_files():
            screen_info = self.parse_screen_file(file_path)
            if screen_info:
                screens[screen_info.name] = screen_info

        return screens

    def get_screen_widgets_summary(self, screen_name: str) -> dict[str, Any]:
        """Get a summary of widgets for a screen.

        Args:
            screen_name: Name of the screen (e.g., 'home', 'charts').

        Returns:
            Dict with widget summary suitable for prompts.
        """
        screens = self.parse_all_screens()
        screen = screens.get(screen_name)

        if not screen:
            return {"error": f"Screen '{screen_name}' not found"}

        # Flatten widgets for summary
        widgets_by_type: dict[str, list[dict[str, Any]]] = {}
        all_ids: list[str] = []
        tabs: list[str] = []

        def process_widget(widget: WidgetInfo) -> None:
            if widget.widget_type not in widgets_by_type:
                widgets_by_type[widget.widget_type] = []

            widget_entry: dict[str, Any] = {}
            if widget.widget_id:
                widget_entry["id"] = widget.widget_id
                all_ids.append(widget.widget_id)
            if widget.text_content:
                widget_entry["text"] = widget.text_content
            if widget.classes:
                widget_entry["classes"] = widget.classes
            if widget.tab_id:
                widget_entry["tab"] = widget.tab_id
                if widget.tab_id not in tabs:
                    tabs.append(widget.tab_id)

            if widget_entry:
                widgets_by_type[widget.widget_type].append(widget_entry)

            # Process children
            for child in widget.children:
                process_widget(child)

        for widget in screen.widgets:
            process_widget(widget)

        return {
            "name": screen.name,
            "class": screen.class_name,
            "docstring": screen.docstring,
            "css_path": screen.css_path,
            "widgets": widgets_by_type,
            "widget_ids": all_ids,
            "tabs": tabs,
        }


# Module-level instance for convenience
_parser: ScreenParser | None = None


def get_parser() -> ScreenParser:
    """Get or create the module-level parser instance.

    Returns:
        ScreenParser instance.
    """
    global _parser
    if _parser is None:
        _parser = ScreenParser()
    return _parser


def get_screen_widgets(screen_name: str) -> dict[str, Any]:
    """Get widget summary for a screen.

    Convenience function for prompt generation.

    Args:
        screen_name: Name of the screen.

    Returns:
        Widget summary dict.
    """
    return get_parser().get_screen_widgets_summary(screen_name)
