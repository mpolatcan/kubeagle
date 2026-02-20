"""Constants for TUI screenshot capture."""

from __future__ import annotations

import errno
import re

# Version number
VERSION = "1.1.0"

# Delay presets for different analysis modes
# Quick: Fast visual check (default for most use cases)
QUICK_DELAYS: list[float] = [5.0]
# Standard: Normal UX review with time for data loading
STANDARD_DELAYS: list[float] = [10.0]
# Freeze detection: Multiple captures to detect stuck states
FREEZE_DELAYS: list[float] = [30.0, 60.0, 90.0]

# Default delays - use QUICK for fast feedback
# To use freeze detection, explicitly pass --delays 30,60,90
DEFAULT_DELAYS: list[float] = QUICK_DELAYS

# Fallback delay when no delays are specified
FALLBACK_DELAY: list[float] = [2.0]

# Errno codes for PNG write permission errors
PNG_WRITE_ERRNOS = frozenset([errno.EACCES, errno.EPERM, errno.EROFS])

# Minimum scroll thresholds to avoid false positives
# Textual may report small max_scroll values even when content fits
# Horizontal is measured in pixels, vertical in character rows
MIN_HORIZONTAL_SCROLL_PIXELS = 5  # Minimum pixels to consider horizontal scrolling needed
MIN_VERTICAL_SCROLL_ROWS = 1  # Minimum rows to consider vertical scrolling needed

# Maximum iterations for widget parent traversal (safety against infinite loops)
MAX_PARENT_ITERATIONS = 100

# Minimum valid dimensions for terminal size (columns x rows)
# These minimums ensure the terminal is large enough for meaningful screenshots
MIN_COLS = 10  # Minimum columns for readable output
MIN_ROWS = 5   # Minimum rows for visible content

# Default terminal size for screenshots (as tuple for internal use)
DEFAULT_TERMINAL_SIZE: tuple[int, int] = (160, 50)

# Default terminal size for CLI (as string for Typer options)
DEFAULT_TERMINAL_SIZE_STR: str = "160x50"

# File extensions to include in results (without dot, matching Path.suffix behavior)
CAPTURED_EXTENSIONS = frozenset(["png", "svg"])

# Default output directory for screenshots
DEFAULT_OUTPUT_DIR = "/tmp/screenshots"

# Default screen limit for live discovery
DEFAULT_SCREEN_LIMIT = 3

# Default PNG scale factor
DEFAULT_PNG_SCALE = 1.0

# Navigation delay for dynamic discovery (same as CaptureConfig.initial_delay)
NAVIGATION_DELAY = 2.0

# Minimum tabs required for multi-tab capture
# A single tab means no tab switching is needed, so we skip multi-tab processing
MIN_TABS_FOR_MULTI_TAB_CAPTURE = 2  # Only capture multiple tabs when 2+ tabs exist

# Default number of scroll positions to capture (excludes 0% which is base screenshot)
# A value of 5 captures scroll positions at 20%, 40%, 60%, 80%, 100%
DEFAULT_SCROLL_STEPS = 5

# Minimum number of parts expected when parsing replace transform
MIN_REPLACE_PARTS = 2

# Translation table for filename sanitization (str.translate is faster than multiple replace)
FILENAME_SANITIZE_TABLE = str.maketrans(
    {
        "/": "-",
        "\\": "-",
        " ": "-",
        "(": "",
        ")": "",
        ":": "-",
    }
)

# Retry settings for widget discovery (when widgets are recreated after compose)
MAX_WIDGET_FIND_RETRIES = 2  # Number of retry attempts
WIDGET_FIND_RETRY_DELAY = 0.2  # Seconds to wait between retries

# Operation timeout settings (seconds)
# These prevent individual operations from hanging indefinitely
SCREENSHOT_TIMEOUT = 30.0  # Timeout for individual screenshot export
SCROLL_CAPTURE_TIMEOUT = 20.0  # Timeout for scrolling to each position
PNG_CONVERSION_TIMEOUT = 30.0  # Timeout for SVG to PNG conversion
TAB_SWITCH_TIMEOUT = 10.0  # Timeout for tab switching operations

# Widget types that should NEVER be included - these are UI chrome, not content
EXCLUDED_TYPES: frozenset[str] = frozenset([
    "Button",
    "Static",
    "Label",
    "Header",
    "Footer",
    "FooterKey",
    "Horizontal",
    "Vertical",
    "Container",
    "Underline",
    "ContentTab",
    "ContentTabs",
    "TabbedContent",
    "ContentSwitcher",
    "TabPane",
    "LoadingIndicator",
    "Input",
    "Switch",
    "Checkbox",
    "RadioButton",
    "RadioSet",
    "ProgressBar",
    "Placeholder",
    "Rule",
    "Markdown",
    "MarkdownViewer",
])

# Widget class names whose parents should be skipped (internal scrollables)
# These are widgets that contain internal ScrollableContainers that shouldn't be captured
SKIP_PARENT_CLASSES: frozenset[str] = frozenset([
    "Footer",  # Footer uses internal ScrollableContainer for key bindings
    "Header",  # Header may use internal scrollable
])

# Scrollable widget types with their scroll capabilities
# Dict keyed by type_name for O(1) lookup: type_name -> (selector, scroll_x, scroll_y)
SCROLLABLE_TYPES: dict[str, tuple[str, bool, bool]] = {
    "DataTable": ("DataTable", True, True),
    "ListView": ("ListView", False, True),
    "Tree": ("Tree", False, True),
    "DirectoryTree": ("DirectoryTree", False, True),
    "OptionList": ("OptionList", False, True),
    "SelectionList": ("SelectionList", False, True),
    "RichLog": ("RichLog", False, True),
    "TextArea": ("TextArea", True, True),
    # Container types that can scroll
    "ScrollableContainer": ("ScrollableContainer", True, True),
    "VerticalScroll": ("VerticalScroll", False, True),
    "HorizontalScroll": ("HorizontalScroll", True, False),
}

# Screen aliases for compatibility
# Maps alias_name -> canonical_name
# e.g., "team_statistics" is an alias for "team_stats"
SCREEN_ALIAS_MAP = {
    "team_statistics": "team_stats",
    "teams": "team",
}

# Scrollable type names extracted from SCROLLABLE_TYPES (frozenset for immutability)
SCROLLABLE_TYPE_NAMES: frozenset[str] = frozenset(SCROLLABLE_TYPES.keys())

# Pre-compiled regex patterns for tab label cleaning (performance optimization)
LABEL_CLEAN_PATTERN_1 = re.compile(r"\s*\(\d+\)$")
LABEL_CLEAN_PATTERN_2 = re.compile(r"[\s-]+\d+$")

# Pre-compiled regex pattern for parsing replace(old, new) transforms
REPLACE_TRANSFORM_PATTERN = re.compile(
    r"replace\s*\(\s*['\"](.*?)['\"]\s*,\s*['\"](.*?)['\"]\s*\)"
)

# Pre-compiled regex for mixed quote styles fallback
MIXED_QUOTE_PATTERN = re.compile(r'''^['"](.*)['"]\s*,\s*['"](.*)['"]$''')

# Length of "replace(" prefix for slicing
REPLACE_PREFIX_LEN = len("replace(")

# Cache size limits for discovery operations
# Visibility cache: stores widget visibility state to avoid repeated parent traversal
MAX_VISIBILITY_CACHE_SIZE = 1000  # Limit cache size to prevent unbounded growth

# Scrollables cache: stores discovered scrollable widgets keyed by (screen_id, primary_only)
MAX_SCROLLABLES_CACHE_SIZE = 128

# Widget cache: stores widget references for O(1) lookup by widget_id
MAX_WIDGET_CACHE_SIZE = 500

# Cache eviction settings
# Minimum number of items to evict when cache exceeds max size
CACHE_EVICTION_MIN_ITEMS = 10  # For visibility cache
WIDGET_CACHE_EVICTION_MIN = 50  # For widget cache (larger due to more entries)

# Scrollables cache eviction count
SCROLLABLES_CACHE_EVICTION_COUNT = 5

# Retry and timeout settings
CAPTURE_MAX_RETRIES = 5  # Maximum retry attempts for stuck capture
THREAD_JOIN_TIMEOUT = 0.5  # Timeout for joining watchdog thread (seconds)
RETRY_SLEEP_LONG = 1.0  # Sleep duration after failed capture attempt (seconds)

# Initialization sleep settings
INIT_SLEEP_DELAY = 0.5  # Initial delay for app startup (seconds)
INIT_SLEEP_TIMEOUT = 5.0  # Timeout for initial sleep (seconds)

# Empty dimensions constant for dimension detection failures
EMPTY_DIMENSIONS: dict[str, int] = {
    "content_height": 0,
    "content_width": 0,
    "viewport_height": 0,
    "viewport_width": 0,
    "scrollable_height": 0,
    "scrollable_width": 0,
}


def get_canonical_name(name: str) -> str:
    """Get the canonical name for a screen name.

    Args:
        name: Screen name or alias.

    Returns:
        Canonical screen name.

    """
    return SCREEN_ALIAS_MAP.get(name, name)


# =============================================================================
# Response Parser Constants
# =============================================================================

# Patterns for extracting structured data from AI responses
RESPONSE_STATUS_PATTERNS: list[str] = [
    r"STATUS:\s*(OK|ISSUES|PASS|PARTIAL|FAIL)",
    r"OVERALL:\s*(PASS|NEEDS_WORK|FAIL)",
    r"VERDICT:\s*(NORMAL|FROZEN|STUCK|PASS|FAIL)",
    r"OVERALL_VERDICT:\s*(PASS|NEEDS_WORK|FAIL)",
]

RESPONSE_DATA_STATUS_PATTERNS: list[str] = [
    r"DATA_STATUS:\s*(LOADED|LOADING|EMPTY|PARTIAL)",
    r"DATA_LOADED:\s*(YES|NO|PARTIAL)",
    r"DATA_PRESENT:\s*(YES|NO|PARTIAL)",
]

RESPONSE_LOADING_PATTERNS: list[str] = [
    r"LOADING_VISIBLE:\s*(YES|NO)",
    r"LOADING_INDICATOR:\s*(VISIBLE|HIDDEN)",
]

RESPONSE_SCORE_PATTERNS: dict[str, str] = {
    "visual": r"VISUAL_SCORE:\s*(\d+)",
    "data": r"DATA_SCORE:\s*(\d+)",
    "ux": r"UX_SCORE:\s*(\d+)",
    "layout": r"LAYOUT_SCORE:\s*(\d+)",
}

RESPONSE_CONFIDENCE_PATTERNS: list[str] = [
    r"CONFIDENCE:\s*(HIGH|MEDIUM|LOW)",
]

# Severity keywords in AI responses (lowercased for faster comparison)
SEVERITY_KEYWORDS: dict[str, frozenset[str]] = {
    "CRITICAL": frozenset([
        "critical", "crash", "broken", "unusable", "blocks", "cannot",
        "fails", "error", "exception", "stuck permanently",
    ]),
    "HIGH": frozenset([
        "major", "significant", "important", "serious", "frozen",
        "empty when", "not loading", "missing data", "stuck",
    ]),
    "MEDIUM": frozenset([
        "moderate", "noticeable", "should", "could improve",
        "alignment", "spacing", "inconsistent",
    ]),
    "LOW": frozenset([
        "minor", "small", "slight", "polish", "nice to have",
        "optional", "consider", "might",
    ]),
}

# Category keywords for finding classification (lowercased for faster comparison)
CATEGORY_KEYWORDS: dict[str, frozenset[str]] = {
    "data_loading": frozenset([
        "loading", "data", "empty", "populated", "rows", "table",
        "fetch", "stuck", "spinner", "waiting",
    ]),
    "visual": frozenset([
        "layout", "alignment", "spacing", "margin", "padding",
        "color", "contrast", "visual", "design", "style",
    ]),
    "layout_sizing": frozenset([
        "sizing", "size", "width", "height", "proportion", "ratio",
        "truncated", "clipped", "overflow", "wasted", "cramped",
        "squeezed", "dominant", "collapsed", "too small", "too large",
        "not visible", "cut off", "narrow", "wide", "tall", "short",
    ]),
    "interaction": frozenset([
        "button", "click", "input", "focus", "keyboard", "navigation",
        "interactive", "response", "action",
    ]),
    "accessibility": frozenset([
        "contrast", "accessibility", "a11y", "wcag", "screen reader",
        "focus indicator", "label", "aria",
    ]),
    "performance": frozenset([
        "slow", "lag", "freeze", "unresponsive", "timeout",
        "performance", "delay",
    ]),
    "content": frozenset([
        "text", "label", "title", "description", "message",
        "placeholder", "content", "copy",
    ]),
}


# =============================================================================
# Expectation Constants
# =============================================================================

# Naming patterns that indicate widget purpose (pattern -> expectation type)
WIDGET_ID_PATTERNS: dict[str, str] = {
    # Stats and counts - should show numbers
    r"^stat[-_]": "should_show_number",
    r"[-_]count$": "should_show_number",
    r"[-_]total$": "should_show_number",
    r"^kpi[-_]": "should_show_number",
    # Loading indicators - should hide
    r"^loading[-_]": "should_hide",
    r"[-_]loading$": "should_hide",
    r"[-_]spinner$": "should_hide",
    # Status indicators - should show state
    r"[-_]status$": "should_show_status",
    r"^status[-_]": "should_show_status",
    # Tables and lists - should have data
    r"[-_]table$": "should_have_data",
    r"[-_]list$": "should_have_data",
}

# Widget types with inherent expectations (type -> expectation type)
WIDGET_TYPE_EXPECTATIONS: dict[str, str] = {
    "DataTable": "should_have_data",
    "ListView": "should_have_data",
    "Tree": "should_have_data",
    "SelectionList": "should_have_data",
    "LoadingIndicator": "should_hide",
    "ProgressBar": "should_hide",
    "Button": "should_be_interactive",
    "Input": "should_be_interactive",
}

# Combined regex for loading/placeholder text detection (pre-compiled)
EXPECTATION_LOADING_REGEX = re.compile(
    r"^(loading\.{0,3}|please wait|fetching|connecting|initializing|n/a|-+|\.{3,})$",
    re.IGNORECASE,
)

# CSS class patterns that indicate states (pattern -> state name)
CSS_STATE_PATTERNS: dict[str, str] = {
    r"status[-_]connected": "Connected",
    r"status[-_]disconnected": "Disconnected",
    r"status[-_]error": "Error",
    r"status[-_]warning": "Warning",
    r"status[-_]loading": "Loading",
    r"status[-_]success": "Success",
    r"status[-_]ready": "Ready",
}


# =============================================================================
# UX Guidelines Constants
# =============================================================================

# Layout and sizing best practices
LAYOUT_SIZING_GUIDELINES = """
## Layout & Component Sizing Best Practices

### Space Distribution
- Content area should occupy ≥60% of vertical space
- Primary content should occupy ≥70% of horizontal space
- Headers/footers should have fixed, minimal heights
- Sidebars should be 20-30% width (not dominant)

### Component Sizing Rules
| Component | Sizing Rule |
|-----------|-------------|
| Tables | Use `height: 1fr` to fill available space |
| Headers | Fixed height (3-5 rows max) |
| Footers | Fixed height (1-2 rows for keybindings) |
| Sidebars | Percentage width (20-30%), not fixed pixels |
| Panels | Proportional heights using fr units |
| Stats/KPIs | Auto-width based on content, consistent heights |

### Common Anti-Patterns to Avoid
- Fixed pixel heights on content containers (use fr/% instead)
- Missing `min-height`/`max-height` constraints
- `width: auto` on containers (can collapse unexpectedly)
- Nested scrollables without proper bounds
- Header/footer taking >40% of screen height

### Textual CSS Best Practices
- Use `height: 1fr` for flexible content areas
- Use `max-height: 100%` to prevent overflow
- Use `overflow-y: auto` for scrollable content
- Use `min-width` to prevent column collapse
- Grid layouts: `grid-size: 1 1` for single-cell, `grid-rows: auto 1fr auto` for header/content/footer
"""

# Screen-specific guidelines
SCREEN_UX_GUIDELINES: dict[str, str] = {
    "home": """
### Dashboard Best Practices
- KPIs should be at-a-glance readable
- Most critical metrics should be largest/topmost
- Trend indicators (up/down arrows) add context
- Quick actions should be clearly labeled
- Alert counts should be prominently displayed
- Consider showing "last updated" timestamp
""",
    "charts": """
### Data Browser Best Practices
- Search should be fast and intuitive
- Filters should show current state clearly
- Tab counts help users know content volume
- Sorting options should be available
- Row selection should be visually clear
- Consider showing record count (X of Y visible)
""",
    "cluster": """
### Cluster View Best Practices
- Health status should be immediately visible
- Critical issues (NotReady nodes) should be highlighted
- Resource usage should show thresholds (warning at 80%+)
- Events should be time-sorted (newest first)
- Consider sparklines for resource trends
""",
    "optimizer": """
### Recommendations Best Practices
- Severity should be color-coded
- Group by category for easier scanning
- Show impact/benefit of each recommendation
- Provide clear action steps
- Consider "fix all" batch option for low-risk items
""",
    "settings": """
### Settings Best Practices
- Current values should be clearly shown
- Changes should have immediate feedback
- Invalid values should show inline errors
- Consider "Reset to defaults" option
- Group related settings together
""",
}

# =============================================================================
# Prompt Preamble
# =============================================================================

# Role framing, image context, and negative constraints applied to all prompts
PROMPT_PREAMBLE = """You are a senior UX engineer reviewing a terminal-based TUI application.

**Image context**: This is a PNG screenshot of a Textual framework TUI app rendered in a terminal. Expect dark backgrounds, box-drawing characters, ANSI colors, and monospace text.

**Constraints**:
- Report ONLY what is visually observable in the screenshot.
- Do NOT speculate about functionality, screens, or widgets you cannot see.
- Do NOT suggest changes outside the visible screen area.
- If an element is ambiguous, note the ambiguity rather than guessing.
"""


# Improvement suggestion prompts by analysis type
IMPROVEMENT_PROMPTS: dict[str, str] = {
    "layout": """
## Layout Improvement Opportunities

Suggest up to 3 improvements, ranked by impact:
1. **Space Utilization** - Could content use available space better?
2. **Component Proportions** - Are ratios optimal for user tasks?
3. **Content Priority** - Does sizing reflect content importance?

Format improvements as:
IMPROVEMENT: [description]
CSS_FIX: [suggested CSS change]
BENEFIT: [user benefit]
EFFORT: LOW | MEDIUM | HIGH
CONFIDENCE: HIGH | MEDIUM | LOW
""",
    "visual": """
## Improvement Opportunities

Suggest up to 3 improvements, ranked by impact:
1. **Visual Hierarchy** - Could important data be more prominent?
2. **Information Density** - Is screen too sparse or too crowded?
3. **Color Usage** - Could status colors be more meaningful?

Format improvements as:
IMPROVEMENT: [description]
BENEFIT: [user benefit]
EFFORT: LOW | MEDIUM | HIGH
CONFIDENCE: HIGH | MEDIUM | LOW
""",
    "data": """
## Improvement Opportunities

Suggest up to 3 improvements, ranked by impact:
1. **Empty States** - Could empty tables show helpful messages?
2. **Loading Feedback** - Could loading be more informative?
3. **Data Formatting** - Could numbers/dates be formatted better?

Format improvements as:
IMPROVEMENT: [description]
BENEFIT: [user benefit]
EFFORT: LOW | MEDIUM | HIGH
CONFIDENCE: HIGH | MEDIUM | LOW
""",
    "full": """
## Improvement Opportunities

Suggest up to 5 improvements, ranked by impact across all aspects:
- Visual design (layout, spacing, color, contrast)
- User experience (workflow, discoverability, error handling)
- Data presentation (formatting, empty states, visualization)
- Accessibility (WCAG AA contrast, keyboard nav, labels)

Format each improvement as:
IMPROVEMENT: [description]
CATEGORY: visual | ux | data | accessibility
BENEFIT: [user benefit]
EFFORT: LOW | MEDIUM | HIGH
PRIORITY: HIGH | MEDIUM | LOW
CONFIDENCE: HIGH | MEDIUM | LOW
""",
    "standard": """
## Improvement Opportunities

Suggest up to 3 quick wins (low-effort, high-impact):

Format as:
IMPROVEMENT: [description]
BENEFIT: [user benefit]
EFFORT: LOW | MEDIUM | HIGH
CONFIDENCE: HIGH | MEDIUM | LOW
""",
}
