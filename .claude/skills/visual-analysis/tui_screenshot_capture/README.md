# TUI Screenshot Capture Utility

> **Location**: `.claude/skills/visual-analysis/tui_screenshot_capture/`
> **Version**: 1.1.0

Comprehensive screenshot capture tool for the EKS Helm Reporter TUI application with advanced features for visual testing, AI-powered analysis, and documentation.

## Running the Tool

Since this module is located under the `.claude/skills/visual-analysis/` directory, use PYTHONPATH to run it:

```bash
source venv/bin/activate
PYTHONPATH=.claude/skills/visual-analysis python -m tui_screenshot_capture --help
```

Or set up an alias for convenience:
```bash
alias capture-tui='PYTHONPATH=.claude/skills/visual-analysis python -m tui_screenshot_capture'
capture-tui --help
```

## Features

| Feature | Description |
|---------|-------------|
| **Multi-Delay Capture** | Built-in `--delays` option with presets: quick (5s), standard (10s), freeze (30s,60s,90s) |
| **Single-Run Capture** | Captures screenshots within a single app instance |
| **Resolution Control** | Specify exact terminal size (COLSxROWS) for consistent screenshots (default: 160x50) |
| **Global Timeout** | `--timeout` option prevents entire capture from hanging indefinitely |
| **Watchdog System** | Automatic detection and recovery from stuck capture operations |
| **Screen Discovery** | Dynamically discovers all available screens by reading keyboard bindings |
| **Tab Discovery** | Auto-detects and captures all tabs on screens with tabbed interfaces |
| **Inner Tab Support** | Captures TabbedContent and ContentSwitcher widgets with their tabs |
| **Scroll Capture** | Detects scrollbars and captures evenly distributed positions (20%, 40%, 60%, 80%, 100%) |
| **Smart Scroll** | Calculates scroll positions based on actual content size vs viewport size |
| **Toggle Capture** | Captures both ON and OFF states for toggle switches |
| **Collapsible Capture** | Captures both expanded and collapsed states |
| **PNG Conversion** | Automatically converts SVG screenshots to PNG with configurable scaling (default: 1.0x) |
| **Progress Callbacks** | Real-time progress tracking via callback hooks |
| **Widget Caching** | O(1) widget lookups with LRU eviction for performance |
| **AI Prompt Generation** | Generate contextual prompts for AI vision analysis |
| **Dynamic Widget Discovery** | AST-based parsing of screen code to discover widgets |
| **Auto Expectations** | Auto-generate widget expectations based on naming patterns |
| **Response Parsing** | Parse AI responses into structured findings with severity levels |
| **UX Guidelines** | Built-in UX best practices for TUI applications |

## Installation

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Install required dependencies (for PNG conversion)
pip install cairosvg
```

## Quick Start

```bash
# Set up the environment
source venv/bin/activate
export PYTHONPATH=.claude/skills/visual-analysis
alias capture-tui='python -m tui_screenshot_capture'

# Capture single screen with all auto-detection enabled
capture-tui capture optimizer \
    --charts-path ../web-helm-repository \
    --output /tmp/screenshots

# Or using full python module syntax
PYTHONPATH=.claude/skills/visual-analysis python -m tui_screenshot_capture capture optimizer \
    --charts-path ../web-helm-repository \
    --output /tmp/screenshots

# Capture all screens with default quick delay (5s)
capture-tui capture --all --output /tmp/screenshots --charts-path ../web-helm-repository

# Custom terminal size, freeze detection delays, and timeout
capture-tui capture charts \
    --delays 30,60,90 \
    --size 200x60 \
    --timeout 300 \
    --output /tmp/screenshots \
    --charts-path ../web-helm-repository

# Generate AI analysis prompts
capture-tui generate-prompt home --type full
capture-tui generate-prompt all --type freeze --delay 90
```

## Commands

### `capture` - Capture a Single Screen or All Screens

```bash
capture-tui capture SCREEN [OPTIONS]
capture-tui capture --all [OPTIONS]
```

**Arguments:**
- `SCREEN` - Screen name to capture (e.g., `optimizer`, `charts`, `cluster`)
- Use `--all` or `-a` to capture all screens instead of specifying a screen name

**Options:**
| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--all` | `-a` | False | Capture all available screens |
| `--delays` | `-d` | 5 | Comma-separated delays in seconds (presets: 5=quick, 10=standard, 30,60,90=freeze) |
| `--tab TAB` | `-t` | None | Capture specific tab (e.g., '1', '2') |
| `--all-tabs` | | False | Capture all tabs of the specified screen |
| `--skip-tabs` | | False | Skip automatic tab discovery and capture |
| `--output DIR` | `-o` | /tmp/screenshots | Output directory for screenshots |
| `--size SIZE` | `-s` | 160x50 | Terminal size as COLSxROWS |
| `--png-scale N` | | 1.0 | PNG scale factor |
| `--charts-path PATH` | | None | Path to Helm charts repository |
| `--keep-svg` | | False | Keep SVG files after PNG conversion |
| `--timeout N` | `-T` | 0 | Global timeout for entire capture (0=no timeout) |
| `--scroll-delay N` | | 0.3 | Wait time between scroll positions (seconds) |
| `--tab-delay N` | | 0.5 | Wait time after switching tabs (seconds) |
| `--scroll-vertical` | | auto | Enable vertical scroll capture (omit for auto-detect) |
| `--scroll-horizontal` | | auto | Enable horizontal scroll capture (omit for auto-detect) |
| `--skip-toggles` | | False | Skip toggle state capture |
| `--skip-inner-tabs` | | False | Skip TabbedContent inner tabs capture |
| `--skip-collapsibles` | | False | Skip collapsible widget capture |
| `--skip-all-discovery` | | False | Skip all auto-discovery |

**Scroll Options Syntax:**
- Omit option -> auto-detect scrollable content
- `--scroll-vertical` -> force enable vertical scroll capture
- `--scroll-vertical=false` -> disable vertical scroll capture

### `discover` - Discover Elements and List Screens

```bash
capture-tui discover [OPTIONS]
capture-tui discover --list-screens
```

| Option | Default | Description |
|--------|---------|-------------|
| `--list-screens` | False | List all available screens with their navigation keys |
| `--live` | False | Run live discovery with app instance |
| `--charts-path PATH` | None | Path to Helm charts repository |
| `--screen-limit N` | 3 | Maximum screens to analyze in live discovery |
| `--initial-delay N` | 2.0 | Wait time after navigating to screen |
### `list-elements` - List Discoverable Elements for a Screen

```bash
capture-tui list-elements SCREEN [OPTIONS]
```

Shows tabs, focus targets, toggles, inner tabs, collapsibles, and scrollable widgets for a specific screen.

| Option | Default | Description |
|--------|---------|-------------|
| `--charts-path PATH` | None | Path to Helm charts repository |

### `generate-prompt` - Generate AI Analysis Prompts

```bash
capture-tui generate-prompt SCREEN [OPTIONS]
capture-tui generate-prompt all [OPTIONS]
```

Generates contextual prompts for AI vision analysis using dynamic widget discovery from actual screen code.

**Arguments:**
- `SCREEN` - Screen name(s) to generate prompts for (e.g., `home`, `charts`, `cluster`)
- Use `all` to generate prompts for all screens

**Options:**
| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--type` | `-t` | standard | Analysis type: quick, standard, data, freeze, visual, layout, full |
| `--delay` | `-d` | None | Capture delay in seconds (for context in prompt) |
| `--format` | `-f` | text | Output format: text, json, markdown |
| `--image-path` | `-i` | None | Image path pattern (use {screen} as placeholder) |

**Analysis Types:**
| Type | Purpose | Delay Preset |
|------|---------|--------------|
| `quick` | Fast rendering check | 5s |
| `standard` | Normal UX review with expected elements | 10s |
| `data` | Focus on data loading verification | 10s |
| `freeze` | Compare with previous for stuck detection | 30s, 60s, 90s |
| `visual` | Visual design quality audit | 10s |
| `layout` | Layout & component sizing analysis | 10s |
| `full` | Comprehensive UX audit | 10s |

**Examples:**
```bash
# Generate prompt for single screen
capture-tui generate-prompt home --type full

# Generate prompts for multiple screens
capture-tui generate-prompt home cluster charts --type data

# Generate prompts for all screens with freeze detection context
capture-tui generate-prompt all --type freeze --delay 90

# Generate with image path for copy-paste usage
capture-tui generate-prompt home --image-path "/tmp/screenshots/{screen}/{screen}-090s.png"

# Output as JSON for programmatic use
capture-tui generate-prompt home --type full --format json
```

## Usage Examples

### Basic Capture

```bash
# Capture optimizer screen with full auto-discovery
capture-tui capture optimizer --charts-path ../web-helm-repository
```

### Multi-Delay Capture (Freeze Detection)

The CLI supports multi-delay capture with presets for different use cases:

```bash
# Quick capture (default): 5 seconds
capture-tui capture cluster --charts-path ../web-helm-repository

# Standard capture: 10 seconds
capture-tui capture cluster --delays 10 --charts-path ../web-helm-repository

# Freeze detection: 30s, 60s, 90s
capture-tui capture cluster --delays 30,60,90 --charts-path ../web-helm-repository

# Custom delays
capture-tui capture cluster --delays 10,20,30 --charts-path ../web-helm-repository
```

**Delay Presets:**
| Preset | Delays | Use Case |
|--------|--------|----------|
| Quick | 5s | Fast visual check (default) |
| Standard | 10s | Normal UX review |
| Freeze | 30s, 60s, 90s | Stuck/frozen state detection |

**How multi-delay works:**
- At each delay, a base screenshot is captured
- At the **final delay**, full discovery captures are performed (scroll positions, toggles, inner tabs, collapsibles)
- This allows comparing screenshots at different time points to detect frozen/stuck UI elements

### Timeout Protection

Prevent long-running or stuck captures with the `--timeout` option:

```bash
# 5-minute timeout for all screens
capture-tui capture --all --timeout 300 --charts-path ../web-helm-repository

# 2-minute timeout for single screen
capture-tui capture optimizer --timeout 120 --charts-path ../web-helm-repository

# No timeout (default behavior)
capture-tui capture charts --timeout 0 --charts-path ../web-helm-repository
```

### Tab Capture

```bash
# Capture specific tab
capture-tui capture charts --tab 2 --charts-path ../web-helm-repository

# Capture all tabs of a screen
capture-tui capture charts --all-tabs --charts-path ../web-helm-repository

# Skip tab discovery (capture default view only)
capture-tui capture charts --skip-tabs --charts-path ../web-helm-repository
```

### Toggle Capture

```bash
# Captures both ON and OFF states for all toggles
capture-tui capture optimizer --charts-path ../web-helm-repository

# Skip toggle capture
capture-tui capture optimizer --skip-toggles --charts-path ../web-helm-repository
```

### Collapsible Widget Capture

```bash
# Captures both expanded and collapsed states
capture-tui capture settings --charts-path ../web-helm-repository

# Skip collapsible capture
capture-tui capture settings --skip-collapsibles --charts-path ../web-helm-repository
```

### Inner Tab Capture

```bash
# Captures TabbedContent and ContentSwitcher tabs
capture-tui capture charts --charts-path ../web-helm-repository

# Skip inner tabs (only capture keyboard tabs)
capture-tui capture charts --skip-inner-tabs --charts-path ../web-helm-repository
```

### Scroll Capture

```bash
# Auto-detect and capture scroll positions (default behavior)
capture-tui capture optimizer --charts-path ../web-helm-repository

# Explicitly disable scroll capture
capture-tui capture optimizer --scroll-vertical=false --scroll-horizontal=false --charts-path ../web-helm-repository

# Force vertical scroll capture
capture-tui capture optimizer --scroll-vertical --charts-path ../web-helm-repository

# Capture both vertical and horizontal scrolling
capture-tui capture cluster --scroll-vertical --scroll-horizontal --charts-path ../web-helm-repository
```

### Capture All Screens

```bash
# Capture all screens with quick delay (5s default)
capture-tui capture --all --charts-path ../web-helm-repository

# Capture all screens with freeze detection
capture-tui capture --all --delays 30,60,90 --charts-path ../web-helm-repository

# Capture all screens without tabs
capture-tui capture --all --skip-tabs --charts-path ../web-helm-repository

# Skip all auto-discovery (minimal capture)
capture-tui capture --all --skip-all-discovery --charts-path ../web-helm-repository
```

### Discovery Commands

```bash
# List all available screens
capture-tui discover --list-screens

# Show all discoverable elements (static discovery from bindings)
capture-tui discover --charts-path ../web-helm-repository

# Live discovery with running app instance
capture-tui discover --live --charts-path ../web-helm-repository

# List elements for a specific screen
capture-tui list-elements charts --charts-path ../web-helm-repository
```

### AI Analysis Workflow (NEW in 1.1.0)

```bash
# Step 1: Capture screenshots
capture-tui capture charts --charts-path ../web-helm-repository --output /tmp/screenshots

# Step 2: Generate AI analysis prompt
capture-tui generate-prompt charts --type full --image-path "/tmp/screenshots/{screen}/{screen}.png"

# Step 3: Read the image with Claude Code's native multimodal vision
# Claude Code sees images directly via the Read tool - no external MCP needed
```

**Programmatic Usage:**
```python
from tui_screenshot_capture.analysis import (
    generate_analysis_prompt,
    parse_ai_response,
    format_findings_for_prd,
    AnalysisType,
)

# Generate contextual prompt
prompt = generate_analysis_prompt(
    screen_name="charts",
    analysis_type=AnalysisType.FULL,
)

# After getting AI response, parse it
result = parse_ai_response(ai_response_text, "charts")

# Format findings for PRD
if result.findings:
    prd_content = format_findings_for_prd(result.findings)
```

## Output Structure

```
output_dir/
├── home/
│   └── home.png
├── optimizer/
│   ├── optimizer.png                           # Base screenshot
│   ├── optimizer-scroll-v-1.png                # Vertical scroll at 20%
│   ├── optimizer-scroll-v-2.png                # Vertical scroll at 40%
│   ├── optimizer-scroll-v-3.png                # Vertical scroll at 60%
│   ├── optimizer-scroll-v-4.png                # Vertical scroll at 80%
│   ├── optimizer-scroll-v-5.png                # Vertical scroll at 100%
│   ├── optimizer-toggle-category_filter-on.png
│   └── optimizer-toggle-category_filter-off.png
├── charts/
│   ├── charts-all-0.png                        # "all" inner tab (widget 0)
│   ├── charts-team-0.png                       # "team" inner tab
│   ├── charts-toggle-mode-on.png
│   └── charts-toggle-mode-off.png
└── cluster/
    ├── cluster.png
    ├── cluster-scroll-v-1.png
    ├── cluster-collapsible-stats-expanded.png
    └── cluster-collapsible-stats-collapsed.png
```

## Advanced Features

### Screen Aliases

The capture tool supports screen name aliases for convenience:

| Alias | Canonical Name |
|-------|----------------|
| `teams` | `team` |
| `team_statistics` | `team_stats` |

```bash
# Both commands capture the same screen
capture-tui capture teams --charts-path ../web-helm-repository
capture-tui capture team --charts-path ../web-helm-repository
```

### Widget Discovery

The tool automatically discovers and captures:

1. **Scrollable Widgets**: DataTable, ListView, Tree, DirectoryTree, OptionList, SelectionList, RichLog, TextArea
2. **Tabbed Widgets**: TabbedContent, ContentSwitcher
3. **Interactive Widgets**: Switch (toggles), Collapsible

Widget discovery uses the `discover_scrollable_widgets()` function which:
- Queries the current screen for known scrollable widget types
- Filters by visibility (only visible widgets in active tabs)
- Returns widget info including ID, type, scroll capabilities, and explicit ID flag

### Scroll Detection Thresholds

To avoid false positives, scroll capture uses minimum thresholds defined in `constants.py`:
- **Vertical**: `MIN_VERTICAL_SCROLL_ROWS = 1` row of scrollable content
- **Horizontal**: `MIN_HORIZONTAL_SCROLL_PIXELS = 5` pixels of scrollable content

This prevents capturing scroll positions when content fits within the viewport.

### Scroll Position Calculation

Scroll positions are calculated using `calculate_scroll_positions()`:

```python
def calculate_scroll_positions(max_scroll: int, steps: int = 5) -> list[int]:
    """Calculate evenly distributed scroll positions.

    Note: Position 0% is excluded (captured as base screenshot).
    Returns positions for steps 1..N using integer division.
    """
    if max_scroll <= 0 or steps <= 1:
        return []
    return [(i * max_scroll) // steps for i in range(1, steps + 1)]
```

For example, with `max_scroll=100` and `steps=5`:
- Returns `[20, 40, 60, 80, 100]` (20%, 40%, 60%, 80%, 100%)

Default scroll steps is 5 (`DEFAULT_SCROLL_STEPS` constant).

### Visibility Caching

For performance, widget visibility is cached using thread-safe storage in `scrollables.py`:

```python
# Thread-safe visibility cache
_visibility_cache: dict[int, bool] = {}
_visibility_cache_lock = threading.Lock()

def clear_visibility_cache() -> None:
    """Clear the widget visibility cache."""
    with _visibility_cache_lock:
        _visibility_cache.clear()
```

- Cache is cleared on screen navigation
- Cache is cleared on tab switching
- Prevents repeated parent traversal for the same widget
- Uses `MAX_PARENT_ITERATIONS = 100` as a safety limit
- LRU eviction when cache exceeds `MAX_VISIBILITY_CACHE_SIZE = 1000`

### Widget Retry Mechanism

When widgets are recreated (e.g., after app recompose), the capture engine retries:
- `MAX_WIDGET_FIND_RETRIES = 2` attempts
- `WIDGET_FIND_RETRY_DELAY = 0.2` seconds between retries

### Capture Watchdog

The `CaptureWatchdog` class prevents infinite hangs during capture:

```python
class CaptureWatchdog:
    """Watchdog to prevent infinite hangs during capture.

    Uses a separate thread to monitor capture progress and raise
    an exception if the operation takes too long.
    """

    def start(self) -> None: ...
    def pulse(self) -> None: ...      # Reset timer on progress
    def cancel(self) -> None: ...     # Operation completed
    def check_and_raise(self) -> None: ...  # Raise CaptureStuckError if timed out
```

Timeout values for individual operations:
- `SCREENSHOT_TIMEOUT = 30.0` seconds
- `SCROLL_CAPTURE_TIMEOUT = 20.0` seconds
- `PNG_CONVERSION_TIMEOUT = 30.0` seconds
- `TAB_SWITCH_TIMEOUT = 10.0` seconds

### Stable Widget Identification

The `generate_stable_hash()` utility creates stable IDs for widgets that survive recompose:

```python
def generate_stable_hash(*components: str) -> str:
    """Generate a stable hash from string components.

    Uses zlib.adler32 for fast non-cryptographic hashing.
    Returns an 8-character hex string.
    """
```

## Technical Details

### CaptureConfig

The capture engine uses `CaptureConfig` dataclass:

```python
@dataclass(slots=True)
class CaptureConfig:
    """Configuration for capture engine."""
    output_dir: Path = Path("/tmp/screenshots")
    size: tuple[int, int] = (160, 50)  # DEFAULT_TERMINAL_SIZE
    png_scale: float = 1.0
    keep_svg: bool = False
    charts_path: Path | None = None
    delays: list[float] = field(default_factory=lambda: [5.0])  # DEFAULT_DELAYS (QUICK)
    scroll_delay: float = 0.3   # Wait between scroll positions
    tab_delay: float = 0.5      # Wait after tab switch
    capture_timeout: float = 0.0  # Global timeout (0 = no timeout)
```

### State Models

The discovery system uses dataclasses defined in `discovery/state.py`:

```python
class CaptureStatus(Enum):
    """Status of capture operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PARTIAL = "partial"  # Partially completed (some captures failed)
    FAILED = "failed"

@dataclass(slots=True)
class ScrollState:
    """State of a scrollable widget."""
    widget_id: str
    widget_type: str
    has_vertical: bool = False
    has_horizontal: bool = False
    content_height: int = 0
    content_width: int = 0
    viewport_height: int = 0
    viewport_width: int = 0
    max_scroll_y: int = 0
    max_scroll_x: int = 0
    scroll_positions_v: list[int] = field(default_factory=list)
    scroll_positions_h: list[int] = field(default_factory=list)
    captured_positions_v: list[int] = field(default_factory=list)
    captured_positions_h: list[int] = field(default_factory=list)
    status: CaptureStatus = CaptureStatus.PENDING
    has_explicit_id: bool = False
    widget: Any = None  # Direct widget reference for reliable lookup

@dataclass(slots=True)
class TabState:
    """State of a tab (keyboard tab or inner tab)."""
    tab_id: str
    tab_name: str
    tab_key: str | None = None
    tab_index: int = 0
    is_active: bool = False
    scrollables: list[ScrollState] = field(default_factory=list)
    status: CaptureStatus = CaptureStatus.PENDING

@dataclass(slots=True)
class ScreenState:
    """Complete state of a screen for capture tracking."""
    screen_name: str
    nav_key: str
    is_current: bool = False
    scrollables: list[ScrollState] = field(default_factory=list)
    keyboard_tabs: list[TabState] = field(default_factory=list)
    inner_tabs: list[TabState] = field(default_factory=list)
    collapsibles: list[dict[str, Any]] = field(default_factory=list)
    focus_targets: list[dict[str, str]] = field(default_factory=list)
    toggles: list[dict[str, str]] = field(default_factory=list)
    status: CaptureStatus = CaptureStatus.PENDING
    error_message: str | None = None
    total_captures: int = 0
    completed_captures: int = 0

@dataclass(slots=True)
class DiscoveryResult:
    """Complete discovery result for all screens."""
    screens: dict[str, ScreenState] = field(default_factory=dict)
    current_screen: str | None = None
    total_screens: int = 0
    completed_screens: int = 0
    status: CaptureStatus = CaptureStatus.PENDING
```

### Screen Discovery

Screens are discovered by reading keyboard bindings from the `kubeagle/keyboard/` package:
- `keyboard/app.py` contains global navigation bindings (`NAV_BINDINGS`)
- `keyboard/navigation.py` contains screen-specific bindings
- Global navigation bindings (`nav_*`) are mapped to screen names
- No hardcoded screen list needed
- Automatically adapts to new screens

### Screen Analysis

The `analyzer.py` module provides comprehensive screen analysis:

```python
def build_screen_state(app, screen_name, nav_key, is_current=False) -> ScreenState:
    """Build complete state for a screen with all discovered elements."""

def analyze_screen_scrollables(app, primary_only=True) -> list[ScrollState]:
    """Analyze all scrollable widgets in the current screen."""

def analyze_scrollbar(widget, widget_type) -> ScrollState:
    """Analyze a widget to determine its actual scrollbar state."""

def analyze_screen_live(app, screen_name, nav_key) -> ScreenState:
    """Analyze a screen with live app instance."""

def analyze_tab_scrollables(app, tab_state) -> TabState:
    """Analyze scrollables within a tab context."""
```

### Tab Discovery

Tabs are discovered by reading screen-specific keyboard bindings:
- Detects `switch_tab_*` actions for keyboard-accessible tabs
- Detects TabbedContent/ContentSwitcher widgets for inner tabs
- Automatically generates tab names from action/widget labels

### Scroll Detection

```python
def discover_scrollable_widgets(app: Any, primary_only: bool = True) -> list[dict[str, Any]]:
    """Discover scrollable widgets in the current screen.

    Args:
        app: The EKSHelmReporterApp instance.
        primary_only: If True, only return primary content widgets.

    Returns:
        list of dicts with widget info: 'id', 'type', 'widget', 'scroll_x',
        'scroll_y', 'has_explicit_id'.
    """
```

**Detected Widget Types** (from `constants.SCROLLABLE_TYPES`):
| Widget Type | Horizontal | Vertical |
|-------------|-----------|----------|
| `DataTable` | Yes | Yes |
| `ListView` | | Yes |
| `Tree` | | Yes |
| `DirectoryTree` | | Yes |
| `OptionList` | | Yes |
| `SelectionList` | | Yes |
| `RichLog` | | Yes |
| `TextArea` | Yes | Yes |

### Widget Dimension Extraction

The `utils/dimensions.py` module extracts widget dimensions:

```python
def get_widget_dimensions(widget, widget_type) -> dict[str, Any]:
    """Get scrollable dimensions for a widget.

    Returns:
        dict with 'content_height', 'content_width', 'viewport_height',
        'viewport_width', 'scrollable_height', 'scrollable_width'.
    """
```

Special handling for:
- **DataTable**: Uses `row_count` or `rows` for content height
- **ListView**: Uses `row_count` or `len()` for content height
- **Generic widgets**: Uses `max_scroll_y` / `max_scroll_x` directly

### Toggle Discovery

Toggles are discovered from keyboard bindings with `toggle_*` prefix:
- Captures both ON and OFF states
- Returns to original state after capture
- Tracks original state to minimize unnecessary key presses

### Collapsible Discovery

```python
def discover_collapsibles(app) -> list[dict[str, Any]]:
    """Discover Collapsible widgets in the current screen.

    Returns:
        list of dicts with 'id', 'title', 'collapsed', 'widget'.
    """
```

- Captures both expanded and collapsed states
- Uses widget's `toggle()` method or `collapsed` property
- Returns to original state after capture

### TabbedContent Discovery

```python
def discover_tabbed_content(app) -> list[dict[str, Any]]:
    """Discover TabbedContent and ContentSwitcher widgets.

    Returns:
        list of dicts with 'widget_id', 'widget', 'tabs', 'widget_type',
        'has_explicit_id', 'widget_index'.
    """
```

Uses multiple discovery methods:
1. Query TabPane children for real pane IDs
2. Try `_tab_content` internal attribute
3. Fallback to Tabs widget children

### PNG Conversion

Requires `cairosvg` package:
```bash
pip install cairosvg
```

If not installed, SVG files are retained and a warning is displayed.

## Troubleshooting

### `cairosvg not installed` Warning

```
Warning: cairosvg not installed, skipping PNG conversion
Install with: pip install cairosvg
```

**Solution:**
```bash
source venv/bin/activate
pip install cairosvg
```

### No Scrollable Widgets Detected

```
Found 0 scrollable widget(s)
```

**Possible causes:**
- Screen has no scrollable content
- DataTable/ListView widgets are empty
- Widget type not supported
- Content fits within viewport (below minimum scroll thresholds)

### No Tabs Detected

```
Found 0 keyboard tab(s)
Found 0 inner tab widget(s)
```

**Possible causes:**
- Screen has no tabs
- Tab bindings don't follow `switch_tab_*` pattern
- No TabbedContent or ContentSwitcher widgets present

### Widget Not Found After Recompose

```
Widget '...' not found after 3 attempts
```

**Solution:** The capture engine automatically retries with cache invalidation. If this persists:
- Check that the widget has an explicit ID
- Verify the widget exists in the current screen context

### Capture Timeout

```
Capture timed out after Xs for all screens
```

**Solutions:**
- Increase `--timeout` value
- Use `--skip-all-discovery` for faster capture
- Reduce delays with `--delays`

### Capture Stuck

```
Capture operation stuck for Xs - terminating and retrying
```

The watchdog automatically detected a stuck operation. The engine will retry up to `CAPTURE_MAX_RETRIES = 5` times.

### `Charts path not specified` Warning

Some screens require Helm charts data:
```bash
--charts-path ../web-helm-repository
```

## Requirements

- Python 3.10+
- Textual (installed via project dependencies)
- typer (installed via project dependencies)
- loguru (installed via project dependencies)
- cairosvg (optional, for PNG conversion)
- PyYAML (optional, for static manifest fallback in analysis)

## Architecture

```
tui_screenshot_capture/
├── __init__.py            # Package initialization, exports
├── __main__.py            # CLI entry point
├── constants.py           # Constants, configuration, prompts, helper functions
├── analysis/              # AI-powered analysis (NEW in 1.1.0)
│   ├── __init__.py        # Re-exports analysis functions
│   ├── prompt_generator.py # Contextual prompt generation with AnalysisType enum
│   ├── expectations.py    # Auto-generated widget expectations
│   ├── response_parser.py # Parse AI responses into structured findings
│   └── ux_guidelines.py   # UX best practices and screen guidelines
├── cli/                   # Command-line interface
│   ├── __init__.py        # CLI app creation, logging setup
│   ├── capture.py         # capture command (single screen and --all)
│   ├── discover.py        # discover command (with --list-screens)
│   ├── list.py            # list-elements command
│   └── prompt.py          # generate-prompt command (NEW in 1.1.0)
├── core/                  # Core types and exceptions
│   ├── __init__.py        # CaptureConfig, CaptureResult
│   └── exceptions.py      # TuiCaptureError
├── discovery/             # Element discovery
│   ├── __init__.py        # Re-exports discovery functions
│   ├── analyzer.py        # Screen analysis and state building
│   ├── bindings.py        # Keyboard binding discovery
│   ├── screens.py         # Screen discovery
│   ├── screen_parser.py   # AST-based widget discovery from code (NEW in 1.1.0)
│   ├── scrollables.py     # Scrollable widget discovery, caching
│   ├── state.py           # State models (CaptureStatus, ScrollState, etc.)
│   └── widgets.py         # TabbedContent, Collapsible discovery
├── engine/                # Capture engine
│   ├── __init__.py
│   └── capture_engine.py  # State-based capture, CaptureWatchdog
└── utils/                 # Utilities
    ├── __init__.py        # Re-exports utilities
    ├── conversion.py      # SVG to PNG conversion
    ├── dimensions.py      # Widget dimension extraction
    ├── hash.py            # Stable hash generation for widget IDs
    └── parsing.py         # CLI argument parsing
```

### Key Constants (`constants.py`)

| Constant | Value | Description |
|----------|-------|-------------|
| `VERSION` | "1.1.0" | Package version |
| `QUICK_DELAYS` | [5.0] | Quick check delay |
| `STANDARD_DELAYS` | [10.0] | Standard UX review delay |
| `FREEZE_DELAYS` | [30.0, 60.0, 90.0] | Freeze detection delays |
| `DEFAULT_DELAYS` | [5.0] | Default delays (quick) |
| `MIN_VERTICAL_SCROLL_ROWS` | 1 | Minimum rows for vertical scroll detection |
| `MIN_HORIZONTAL_SCROLL_PIXELS` | 5 | Minimum pixels for horizontal scroll detection |
| `MAX_PARENT_ITERATIONS` | 100 | Safety limit for parent traversal |
| `DEFAULT_TERMINAL_SIZE` | (160, 50) | Default terminal dimensions |
| `DEFAULT_SCROLL_STEPS` | 5 | Number of scroll positions to capture |
| `MAX_WIDGET_FIND_RETRIES` | 2 | Retry attempts for widget discovery |
| `WIDGET_FIND_RETRY_DELAY` | 0.2 | Seconds between retries |
| `SCROLLABLE_TYPES` | dict | Widget types with scroll capabilities |
| `EXCLUDED_TYPES` | frozenset | Widget types to exclude (UI chrome) |
| `SCREEN_ALIAS_MAP` | dict | Screen name aliases |
| `SCREENSHOT_TIMEOUT` | 30.0 | Timeout for individual screenshot |
| `SCROLL_CAPTURE_TIMEOUT` | 20.0 | Timeout for scroll operations |
| `PNG_CONVERSION_TIMEOUT` | 30.0 | Timeout for PNG conversion |
| `TAB_SWITCH_TIMEOUT` | 10.0 | Timeout for tab switching |
| `CAPTURE_MAX_RETRIES` | 5 | Max retries for stuck capture |
| `MAX_VISIBILITY_CACHE_SIZE` | 1000 | Visibility cache limit |
| `MAX_SCROLLABLES_CACHE_SIZE` | 128 | Scrollables cache limit |
| `MAX_WIDGET_CACHE_SIZE` | 500 | Widget cache limit |

### AI Analysis Module (`analysis/`) - NEW in 1.1.0

The analysis module provides AI-powered screenshot analysis capabilities:

#### AnalysisType Enum

```python
class AnalysisType(str, Enum):
    QUICK = "quick"      # Fast check: is screen rendering?
    STANDARD = "standard" # Normal check with expected elements
    DATA = "data"        # Focus on data loading
    FREEZE = "freeze"    # Compare with previous for stuck detection
    VISUAL = "visual"    # Visual design quality
    FULL = "full"        # Comprehensive UX audit
```

#### Prompt Generator (`prompt_generator.py`)

Generates contextual prompts using dynamic widget discovery:

```python
from tui_screenshot_capture.analysis import generate_analysis_prompt, AnalysisType

# Generate a prompt for AI vision analysis
prompt = generate_analysis_prompt(
    screen_name="charts",
    analysis_type=AnalysisType.FULL,
    delay_seconds=90.0,
)

# Use with Claude Code's native multimodal vision - just read the image:
# Read(file_path="/tmp/screenshots/charts/charts-090s.png")
# Then analyze using the prompt context
```

#### Response Parser (`response_parser.py`)

Parses AI responses into structured findings:

```python
from tui_screenshot_capture.analysis import (
    parse_ai_response,
    FindingSeverity,
    FindingCategory,
    format_findings_for_prd,
)

# Parse AI response into structured result
result = parse_ai_response(ai_response_text, screen_name="charts")

# Access structured data
print(result.status)          # "PASS", "FAIL", etc.
print(result.data_loaded)     # True/False/None
print(result.loading_visible) # True/False/None
print(result.findings)        # List[UXFinding]

# Format for PRD
prd_text = format_findings_for_prd(result.findings)
```

#### Expectations Generator (`expectations.py`)

Auto-generates widget expectations based on naming patterns:

```python
from tui_screenshot_capture.analysis import (
    generate_screen_expectations,
    format_expectations_for_prompt,
)

# Generate expectations for a screen
expectations = generate_screen_expectations(screen_info)

# Format for inclusion in prompt
expectations_text = format_expectations_for_prompt(expectations)
```

**Widget ID Patterns -> Expectations:**
| Pattern | Expectation |
|---------|-------------|
| `stat-*`, `*-count`, `*-total` | should_show_number |
| `loading-*`, `*-spinner` | should_hide |
| `*-status` | should_show_status |
| `*-table`, `*-list` | should_have_data |

#### UX Guidelines (`ux_guidelines.py`)

Built-in UX best practices for TUI applications:

```python
from tui_screenshot_capture.analysis import (
    get_full_guidelines,
    get_guidelines_for_screen,
    get_improvement_prompt,
)

# Get guidelines for a specific screen
guidelines = get_full_guidelines("charts", "full")
```

### Screen Parser (`discovery/screen_parser.py`) - NEW in 1.1.0

AST-based parsing of screen Python files to discover widgets:

```python
from tui_screenshot_capture.discovery.screen_parser import get_screen_widgets

# Get widget summary for a screen
summary = get_screen_widgets("charts")
# Returns: {
#     "name": "charts",
#     "class": "ChartsScreen",
#     "widgets": {"DataTable": [...], "Static": [...]},
#     "widget_ids": ["table-charts", "stat-count", ...],
#     "tabs": ["all", "team"],
# }
```

## Related Files

- `kubeagle/keyboard/` - Screen and tab bindings (modular package)
  - `app.py` - Global/navigation bindings
  - `navigation.py` - Screen-specific bindings
  - `tables.py` - DataTable bindings
- `kubeagle/app.py` - Main TUI application
