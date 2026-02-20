"""Theme CSS assignment regression tests."""

import re
from pathlib import Path

from textual.app import App

CSS_ROOT = Path("kubeagle/css")
THEME_COLOR_PATTERN = re.compile(
    r"(?:color|background|border[-\w]*):\s*[^;]*\$[a-z0-9-]+", re.IGNORECASE,
)
TOKEN_REF_PATTERN = re.compile(r"\$([a-zA-Z][a-zA-Z0-9_-]*)")
TOKEN_DEF_PATTERN = re.compile(r"^\s*\$([a-zA-Z][a-zA-Z0-9_-]*)\s*:", re.MULTILINE)
CSS_COMMENT_PATTERN = re.compile(r"/\*.*?\*/", re.DOTALL)


def _read_css(path: str) -> str:
    """Read a CSS file from the TUI CSS root."""
    return (CSS_ROOT / path).read_text(encoding="utf-8")


def _get_builtin_theme_tokens() -> set[str]:
    """Get built-in Textual theme variables available to TCSS."""

    class _TokenApp(App):
        CSS = ""

    app = _TokenApp()
    app.theme = "textual-dark"
    return set(app.get_css_variables().keys())


def test_app_has_global_theme_defaults() -> None:
    """App-level CSS should define theme-aware defaults for app and screens."""
    css = _read_css("app.tcss")
    assert "App {" in css
    assert "background: $background;" in css
    assert "color: $text;" in css
    assert "Screen {" in css


def test_screen_roots_define_theme_background_and_color() -> None:
    """All primary screen root selectors should set theme-aware background/text."""
    expected_roots = {
        "screens/cluster_screen.tcss": "ClusterScreen {",
        "screens/charts_explorer.tcss": "ChartsExplorerScreen {",
        "screens/chart_detail_screen.tcss": "ChartDetailScreen {",
        "screens/optimizer_screen.tcss": "OptimizerScreen {",
        "screens/report_export_screen.tcss": "ReportExportScreen {",
        "screens/settings_screen.tcss": "SettingsScreen {",
    }

    for css_path, root_selector in expected_roots.items():
        css = _read_css(css_path)
        assert root_selector in css
        assert "background: $background;" in css
        assert "color: $text;" in css


def test_tab_and_container_widgets_have_theme_text_assignment() -> None:
    """Shared container/tab widgets should carry theme text color defaults."""
    containers_css = _read_css("widgets/custom_containers.tcss")
    assert "CustomContainer {" in containers_css
    assert "CustomHorizontal {" in containers_css
    assert "CustomVertical {" in containers_css
    assert "color: $text;" in containers_css

    tabs_css = _read_css("widgets/custom_tabs.tcss")
    assert "CustomTabs {" in tabs_css
    assert "color: $text;" in tabs_css

    tabbed_content_css = _read_css("widgets/custom_tabbed_content.tcss")
    assert "CustomTabbedContent {" in tabbed_content_css
    assert "color: $text;" in tabbed_content_css

    tab_pane_css = _read_css("widgets/custom_tab_pane.tcss")
    assert "CustomTabPane {" in tab_pane_css
    assert "color: $text;" in tab_pane_css


def test_all_widget_css_files_define_theme_color_assignments() -> None:
    """All widget styles should include at least one theme-aware color assignment.

    Files whose styles migrated entirely to DEFAULT_CSS may contain only
    comments.  Strip comments first and skip empty files.
    """
    widget_css_files = sorted((CSS_ROOT / "widgets").glob("*.tcss"))
    assert widget_css_files

    for css_path in widget_css_files:
        css = css_path.read_text(encoding="utf-8")
        css_no_comments = CSS_COMMENT_PATTERN.sub("", css).strip()
        if not css_no_comments:
            # File contains only comments — styles live in DEFAULT_CSS
            continue
        assert THEME_COLOR_PATTERN.search(css), f"{css_path} should include 'color: $...;'"


def test_footer_uses_theme_compatible_tokens() -> None:
    """Footer colors use Textual design tokens and theme-compatible custom tokens."""
    from kubeagle.widgets.structure.custom_footer import CustomFooter

    app_css = _read_css("app.tcss")
    default_css = CustomFooter.DEFAULT_CSS

    # Custom tokens in app.tcss that don't conflict with Textual design tokens
    assert "$footer-border-color: $primary" in app_css
    assert "$footer-separator-color:" in app_css
    assert "$footer-status-color:" in app_css

    # Self-targeting styles in DEFAULT_CSS use standard Textual design tokens
    assert "$footer-background" in default_css
    assert "$footer-foreground" in default_css


def test_all_css_tokens_are_theme_compatible() -> None:
    """All referenced TCSS tokens should be defined locally or by the active theme."""
    css_files = sorted(CSS_ROOT.rglob("*.tcss"))
    assert css_files

    built_in_tokens = _get_builtin_theme_tokens()
    local_tokens: set[str] = set()

    for css_path in css_files:
        css = CSS_COMMENT_PATTERN.sub("", css_path.read_text(encoding="utf-8"))
        local_tokens.update(TOKEN_DEF_PATTERN.findall(css))

    known_tokens = built_in_tokens | local_tokens
    unknown_references: dict[str, set[str]] = {}

    for css_path in css_files:
        css = CSS_COMMENT_PATTERN.sub("", css_path.read_text(encoding="utf-8"))
        for token in TOKEN_REF_PATTERN.findall(css):
            if token not in known_tokens:
                unknown_references.setdefault(token, set()).add(css_path.as_posix())

    assert not unknown_references, (
        "Unknown TCSS token references found:\n"
        + "\n".join(
            f"{token}: {sorted(paths)}"
            for token, paths in sorted(unknown_references.items())
        )
    )
