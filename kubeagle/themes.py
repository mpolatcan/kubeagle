"""Custom Textual themes for KubEagle branding."""

from textual.app import App
from textual.theme import Theme


def _kubeagle_dark_theme() -> Theme:
    """Build an alternate KubEagle dark theme from the eagle brand palette."""
    return Theme(
        name="KubEagle-Dark",
        primary="#2B84CC",
        secondary="#D2A63B",
        accent="#41B8E8",
        foreground="#DDEBFB",
        background="#071C35",
        success="#36A36F",
        warning="#D2A63B",
        error="#D65159",
        surface="#0E2A4D",
        panel="#163963",
        dark=True,
        variables={
            "block-cursor-background": "#41B8E8",
            "block-cursor-foreground": "#071C35",
            "footer-key-foreground": "#D2A63B",
            "input-selection-background": "#2B84CC 36%",
        },
    )


def _insiderone_dark_theme() -> Theme:
    """Build the legacy InsiderOne dark theme."""
    return Theme(
        name="InsiderOne-Dark",
        primary="#FF6A2A",
        secondary="#C76B3F",
        accent="#FF6A2A",
        foreground="#F5F0EA",
        background="#14121C",
        success="#2FA86D",
        warning="#FF9E2C",
        error="#E5484D",
        surface="#1D1A28",
        panel="#282336",
        dark=True,
        variables={
            "block-cursor-background": "#FF6A2A",
            "block-cursor-foreground": "#14121C",
            "footer-key-foreground": "#FF6A2A",
            "input-selection-background": "#FF6A2A 35%",
        },
    )


def register_kubeagle_themes(app: App[None]) -> None:
    """Register KubEagle themes in the running app."""
    app.register_theme(_kubeagle_dark_theme())
    app.register_theme(_insiderone_dark_theme())
