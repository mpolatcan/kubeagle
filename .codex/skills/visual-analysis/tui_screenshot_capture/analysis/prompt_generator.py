"""Generate contextual prompts for AI vision analysis.

This module generates analysis prompts using dynamic discovery:
- Parse actual screen code to find widgets
- Generate contextual prompts for AI vision tools

The prompts help AI vision tools understand what to look for on each screen.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from loguru import logger

from tui_screenshot_capture.analysis.expectations import (
    format_expectations_for_prompt,
    generate_screen_expectations,
    get_critical_checks,
)
from tui_screenshot_capture.analysis.ux_guidelines import get_full_guidelines
from tui_screenshot_capture.constants import LAYOUT_SIZING_GUIDELINES, PROMPT_PREAMBLE
from tui_screenshot_capture.discovery.screen_parser import get_screen_widgets


class AnalysisType(str, Enum):
    """Types of analysis for screenshots."""

    QUICK = "quick"  # Fast check: is screen rendering?
    STANDARD = "standard"  # Normal check with expected elements
    DATA = "data"  # Focus on data loading
    FREEZE = "freeze"  # Compare with previous for stuck detection
    VISUAL = "visual"  # Visual design quality
    LAYOUT = "layout"  # Layout and component sizing
    FULL = "full"  # Comprehensive UX audit


def _get_dynamic_screen_info(screen_name: str) -> dict[str, Any] | None:
    """Get screen info from dynamic code parsing.

    Args:
        screen_name: Name of the screen.

    Returns:
        Dict with widget info or None if parsing fails.
    """
    try:
        result = get_screen_widgets(screen_name)
        if "error" not in result:
            return result
    except Exception as e:
        logger.debug(f"Dynamic parsing failed: {e}")

    return None


def get_screen_info(screen_name: str) -> dict[str, Any]:
    """Get screen information from dynamic discovery.

    Args:
        screen_name: Name of the screen (e.g., 'home', 'charts').

    Returns:
        Dict with screen info including widgets.
    """
    dynamic_info = _get_dynamic_screen_info(screen_name)
    if dynamic_info:
        return dynamic_info

    # Return minimal info
    return {"name": screen_name, "widgets": {}, "error": "Screen not found"}


def generate_analysis_prompt(
    screen_name: str,
    analysis_type: AnalysisType | str = AnalysisType.STANDARD,
    delay_seconds: float | None = None,
) -> str:
    """Generate a contextual analysis prompt for a screen.

    Uses dynamic code discovery to find actual widgets on the screen,
    then generates prompts that reference those specific elements.

    Args:
        screen_name: Name of the screen (e.g., 'charts', 'cluster').
        analysis_type: Type of analysis to perform.
        delay_seconds: Capture delay in seconds (for context).

    Returns:
        Prompt string for Claude Code's native multimodal vision analysis.
    """
    # Convert string to enum if needed
    if isinstance(analysis_type, str):
        try:
            analysis_type = AnalysisType(analysis_type)
        except ValueError:
            analysis_type = AnalysisType.STANDARD

    # Get screen info (dynamic or static)
    screen_info = get_screen_info(screen_name)

    # Use pre-built prompts for quick/data/freeze/visual/layout
    if analysis_type == AnalysisType.QUICK:
        return _generate_quick_prompt(screen_name, screen_info)
    elif analysis_type == AnalysisType.DATA:
        return _generate_data_prompt(screen_name, screen_info)
    elif analysis_type == AnalysisType.FREEZE:
        return _generate_freeze_prompt(screen_name, screen_info, delay_seconds)
    elif analysis_type == AnalysisType.VISUAL:
        return _generate_visual_prompt(screen_name, screen_info)
    elif analysis_type == AnalysisType.LAYOUT:
        return _generate_layout_prompt(screen_name, screen_info)
    elif analysis_type == AnalysisType.FULL:
        return _generate_full_prompt(screen_name, screen_info)
    else:  # STANDARD
        return _generate_standard_prompt(screen_name, screen_info, delay_seconds)


def _format_widgets_from_dynamic(screen_info: dict[str, Any]) -> str:
    """Format widget info from dynamic discovery into readable text.

    Args:
        screen_info: Dict from get_screen_widgets().

    Returns:
        Formatted string listing widgets.
    """
    lines = []

    widgets = screen_info.get("widgets", {})
    if not widgets:
        return "No specific widgets discovered"

    for widget_type, items in widgets.items():
        if not items:
            continue

        lines.append(f"### {widget_type}")
        for item in items:
            parts = []
            if "id" in item:
                parts.append(f"id='{item['id']}'")
            if "text" in item:
                text = item["text"][:50] + "..." if len(item.get("text", "")) > 50 else item.get("text", "")
                parts.append(f"text='{text}'")
            if "tab" in item:
                parts.append(f"(in tab: {item['tab']})")

            if parts:
                lines.append(f"  - {' '.join(parts)}")

    return "\n".join(lines) if lines else "No specific widgets discovered"


def _format_widget_ids(screen_info: dict[str, Any]) -> str:
    """Format widget IDs as a checklist.

    Args:
        screen_info: Dict from get_screen_widgets().

    Returns:
        Formatted string listing widget IDs.
    """
    ids = screen_info.get("widget_ids", [])
    if not ids:
        return "No widget IDs discovered"

    # Group by prefix for readability
    groups: dict[str, list[str]] = {}
    for widget_id in ids:
        prefix = widget_id.split("-")[0] if "-" in widget_id else "other"
        if prefix not in groups:
            groups[prefix] = []
        groups[prefix].append(widget_id)

    lines = []
    for prefix, widget_ids in sorted(groups.items()):
        lines.append(f"  - {prefix}: {', '.join(sorted(widget_ids))}")

    return "\n".join(lines)


def _generate_quick_prompt(screen_name: str, screen_info: dict[str, Any]) -> str:
    """Generate quick check prompt."""
    base = PROMPT_PREAMBLE
    base += f"\nAnalyze the **{screen_name.upper()}** screen.\n\n"

    # Add docstring if available
    docstring = screen_info.get("docstring")
    if docstring:
        base += f"Screen purpose: {docstring}\n\n"

    # Add widget IDs to look for
    widget_ids = screen_info.get("widget_ids", [])
    if widget_ids:
        base += f"Expected widget IDs: {', '.join(widget_ids[:10])}"
        if len(widget_ids) > 10:
            base += f" (+{len(widget_ids) - 10} more)"
        base += "\n\n"

    base += """Quick Check:
1. Is the screen rendering correctly (no visual corruption, no garbled characters)?
2. Is data loaded (no permanent loading spinners or "Loading..." text)?
3. Are there visible issues: blank areas, overlapping elements, truncated text, or misaligned widgets?

Answer:
STATUS: OK | ISSUES
DETAILS: [brief explanation]
CONFIDENCE: HIGH | MEDIUM | LOW
"""
    return base


def _generate_data_prompt(screen_name: str, screen_info: dict[str, Any]) -> str:
    """Generate data loading check prompt."""
    base = PROMPT_PREAMBLE
    base += f"\nCheck DATA LOADING in the **{screen_name.upper()}** screen.\n\n"

    # Find data-related widgets
    widgets = screen_info.get("widgets", {})
    data_widgets = []

    for widget_type in ["DataTable", "ListView", "Static"]:
        if widget_type in widgets:
            for item in widgets[widget_type]:
                if item.get("id"):
                    data_widgets.append(f"{widget_type}#{item['id']}")

    if data_widgets:
        base += "Data widgets to check:\n"
        for w in data_widgets[:10]:
            base += f"  - {w}\n"
        base += "\n"

    # Add tabs if present
    tabs = screen_info.get("tabs", [])
    if tabs:
        base += f"Tabs present: {', '.join(tabs)}\n\n"

    # Add auto-generated expectations (critical for data check)
    expectations_text = _get_expectations_text(screen_info)
    if expectations_text:
        base += expectations_text
        base += "\n"

    base += """Verify:
1. Are tables/lists populated with data rows?
2. Are statistics showing actual numbers (not "0", "N/A", or placeholder dashes)?
3. Is loading indicator hidden (no visible spinner or "Loading..." text)?
4. Are status badges showing varied states (not all identical)?

Answer:
DATA_STATUS: LOADED | LOADING | EMPTY | PARTIAL
ROW_COUNT: [number or 'N/A']
LOADING_VISIBLE: YES | NO
ISSUES: [list any problems]
CONFIDENCE: HIGH | MEDIUM | LOW
"""
    return base


def _generate_freeze_prompt(
    screen_name: str, screen_info: dict[str, Any], delay_seconds: float | None
) -> str:
    """Generate freeze detection prompt."""
    delay_str = f"{int(delay_seconds)}s" if delay_seconds else "unknown delay"

    base = PROMPT_PREAMBLE
    base += f"\nFREEZE DETECTION for **{screen_name.upper()}** screen at {delay_str}.\n\n"

    docstring = screen_info.get("docstring")
    if docstring:
        base += f"Screen purpose: {docstring}\n\n"

    # Find loading indicators
    widgets = screen_info.get("widgets", {})
    loading_widgets = []

    if "LoadingIndicator" in widgets:
        for item in widgets["LoadingIndicator"]:
            if item.get("id"):
                loading_widgets.append(item["id"])

    # Also check Static widgets for loading text
    if "Static" in widgets:
        for item in widgets["Static"]:
            text = item.get("text", "").lower()
            if "loading" in text:
                if item.get("id"):
                    loading_widgets.append(item["id"])

    if loading_widgets:
        base += f"Loading indicators to check: {', '.join(loading_widgets)}\n\n"

    base += f"""This screenshot was captured after waiting {delay_str}. At this point, data should have loaded.

If a previous screenshot of this screen appears earlier in the conversation, compare them. If this is the only screenshot, evaluate it standalone.

Freeze Indicators:
- Loading spinner STILL visible after 30+ seconds = FROZEN
- Data tables STILL empty when data should exist = DATA_NOT_LOADED
- No visual change from a previous screenshot at an earlier delay = STUCK

Check:
1. Is a loading indicator still visible (spinner, "Loading..." text)?
2. Are data areas still empty or showing placeholder content?
3. If a previous screenshot exists, has anything changed?

Answer:
STATE: LOADED | LOADING | FROZEN | STUCK
LOADING_VISIBLE: YES | NO
DATA_PRESENT: YES | NO | PARTIAL
VERDICT: NORMAL | FROZEN | STUCK
REASON: [explanation]
CONFIDENCE: HIGH | MEDIUM | LOW
"""
    return base


def _generate_visual_prompt(screen_name: str, screen_info: dict[str, Any]) -> str:
    """Generate visual design check prompt."""
    base = PROMPT_PREAMBLE
    base += f"\nVISUAL DESIGN check for **{screen_name.upper()}** screen.\n\n"

    # Add discovered structure
    widgets = screen_info.get("widgets", {})

    # Identify layout elements
    layout_elements = []
    if "Header" in widgets or any(
        "header" in str(w.get("id", "")).lower()
        for wlist in widgets.values()
        for w in wlist
    ):
        layout_elements.append("Header")
    if "Footer" in widgets:
        layout_elements.append("Footer")

    tabs = screen_info.get("tabs", [])
    if tabs:
        layout_elements.append(f"Tabs ({len(tabs)})")

    if "DataTable" in widgets:
        layout_elements.append(f"DataTables ({len(widgets['DataTable'])})")

    if layout_elements:
        base += f"Layout elements found: {', '.join(layout_elements)}\n\n"

    # Add UX guidelines
    guidelines = _get_ux_guidelines(screen_name, "visual")
    if guidelines:
        base += guidelines
        base += "\n"

    base += """Evaluate Visual Quality:

1. LAYOUT: Well-organized header/content/footer structure?
2. ALIGNMENT: Elements properly aligned horizontally and vertically?
3. SPACING: Consistent margins and padding between widgets?
4. TYPOGRAPHY: Text readable with clear size/weight hierarchy?
5. COLORS: Good contrast against dark terminal background, appropriate status colors?
6. COMPLETENESS: All expected widgets visible and not clipped?

Answer:
STATUS: OK | ISSUES
LAYOUT: GOOD | ISSUES
ALIGNMENT: GOOD | ISSUES
CONTRAST: GOOD | LOW
OVERALL: PASS | NEEDS_WORK

CRITICAL_ISSUES:
- [description]

MINOR_ISSUES:
- [description]

CONFIDENCE: HIGH | MEDIUM | LOW
"""
    return base


def _generate_layout_prompt(screen_name: str, screen_info: dict[str, Any]) -> str:
    """Generate layout and component sizing check prompt."""
    base = PROMPT_PREAMBLE
    base += f"\nLAYOUT & SIZING ANALYSIS for **{screen_name.upper()}** screen.\n\n"

    docstring = screen_info.get("docstring")
    if docstring:
        base += f"Screen purpose: {docstring}\n\n"

    # Identify layout structure from widgets
    widgets = screen_info.get("widgets", {})

    # Count major components
    layout_components = []
    if "DataTable" in widgets:
        layout_components.append(f"DataTables: {len(widgets['DataTable'])}")
    if "Static" in widgets:
        # Count stats/panels
        stats = [w for w in widgets["Static"] if "stat" in w.get("id", "").lower()]
        if stats:
            layout_components.append(f"Stats panels: {len(stats)}")

    tabs = screen_info.get("tabs", [])
    if tabs:
        layout_components.append(f"Tabs: {len(tabs)}")

    if layout_components:
        base += f"Layout components found: {', '.join(layout_components)}\n\n"

    # Add layout-specific guidelines
    base += LAYOUT_SIZING_GUIDELINES
    base += "\n"

    base += """## Component Sizing Checklist

| Component | Expected | Check For |
|-----------|----------|-----------|
| Tables | Fill available space | Too narrow? Truncated headers? Wasted space? |
| Panels | Proportional heights | One dominates? Others too small? |
| Headers | Fixed, minimal height | Overlaps content? Text cut off? |
| Footers | Fixed, minimal height | Missing? Overlaps content? |
| Content Area | >=60% screen height | Squeezed by header/footer? |
| Scrollable Areas | Scroll indicators | Content hidden? No scroll hint? |

## Answer Format

LAYOUT_STATUS: GOOD | ISSUES
SIZING_STATUS: GOOD | ISSUES

### Component Assessment
| Component | Size Assessment | Status | Issue (if any) |
|-----------|-----------------|--------|----------------|
| [name] | [description] | OK/BAD | [issue] |

### Proportions
CONTENT_AREA_RATIO: [estimated % of screen]
WASTED_SPACE: YES | NO (describe where)
TRUNCATION: YES | NO (describe what)

### Issues by Severity
CRITICAL:
- [content not visible, data clipped]

HIGH:
- [unusable proportions, major waste of space]

MEDIUM:
- [minor overflow, suboptimal sizing]

### Suspected CSS Issues
- [e.g., Missing height: 1fr, fixed pixels instead of %, width: auto collapse]

OVERALL_VERDICT: PASS | NEEDS_WORK
SUMMARY: [1-2 sentence assessment]
CONFIDENCE: HIGH | MEDIUM | LOW
"""
    return base


def _get_expectations_text(screen_info: dict[str, Any]) -> str:
    """Get formatted expectations text for a screen.

    Args:
        screen_info: Screen info dict.

    Returns:
        Formatted expectations text.
    """
    try:
        expectations = generate_screen_expectations(screen_info)
        if not expectations:
            return ""

        text = format_expectations_for_prompt(expectations)
        critical = get_critical_checks(expectations)

        if critical:
            text += "\n### Critical Checks\n"
            for check in critical:
                text += f"- [ ] {check}\n"

        return text
    except Exception as e:
        logger.debug(f"Failed to generate expectations: {e}")
        return ""


def _generate_standard_prompt(
    screen_name: str, screen_info: dict[str, Any], delay_seconds: float | None
) -> str:
    """Generate standard analysis prompt with expected elements."""
    delay_str = f" (captured at {int(delay_seconds)}s)" if delay_seconds else ""

    base = PROMPT_PREAMBLE
    base += f"\nAnalyze **{screen_name.upper()}** screen{delay_str}.\n\n"

    # Description
    docstring = screen_info.get("docstring")
    if docstring:
        base += f"## Purpose\n{docstring}\n\n"

    # Widget summary
    base += "## Discovered Elements\n"
    base += _format_widgets_from_dynamic(screen_info)
    base += "\n\n"

    # Widget IDs
    widget_ids = screen_info.get("widget_ids", [])
    if widget_ids:
        base += "## Widget IDs\n"
        base += _format_widget_ids(screen_info)
        base += "\n\n"

    # Tabs
    tabs = screen_info.get("tabs", [])
    if tabs:
        base += f"## Tabs\n{', '.join(tabs)}\n\n"

    # Auto-generated expectations
    expectations_text = _get_expectations_text(screen_info)
    if expectations_text:
        base += expectations_text
        base += "\n"

    base += """## Analysis

Answer these questions:
1. Are expected elements visible in the screenshot?
2. Is data loaded (tables populated with rows, stats showing numbers)?
3. Is loading indicator hidden (no spinner or "Loading..." text)?
4. Any visual issues (overlap, truncation, blank areas, misalignment)?

## Response Format

STATUS: PASS | PARTIAL | FAIL
DATA_LOADED: YES | NO | PARTIAL
LOADING_VISIBLE: YES | NO

ELEMENTS_FOUND:
- [list visible elements by ID]

MISSING_ELEMENTS:
- [list missing expected elements]

ISSUES:
- [SEVERITY] description

VERDICT: [brief summary]
CONFIDENCE: HIGH | MEDIUM | LOW
"""
    return base


def _get_ux_guidelines(screen_name: str, analysis_type: str) -> str:
    """Get UX guidelines and improvement prompts.

    Args:
        screen_name: Name of the screen.
        analysis_type: Type of analysis.

    Returns:
        Guidelines text.
    """
    try:
        return get_full_guidelines(screen_name, analysis_type)
    except Exception as e:
        logger.debug(f"Failed to get UX guidelines: {e}")
        return ""


def _generate_full_prompt(screen_name: str, screen_info: dict[str, Any]) -> str:
    """Generate comprehensive UX audit prompt."""
    base = PROMPT_PREAMBLE
    base += f"\nCOMPREHENSIVE UX AUDIT of **{screen_name.upper()}** screen.\n\n"

    docstring = screen_info.get("docstring")
    if docstring:
        base += f"## Screen Purpose\n{docstring}\n\n"

    # Full widget inventory
    base += "## Widget Inventory\n"
    base += _format_widgets_from_dynamic(screen_info)
    base += "\n\n"

    # Widget IDs
    widget_ids = screen_info.get("widget_ids", [])
    if widget_ids:
        base += f"## All Widget IDs ({len(widget_ids)} total)\n"
        base += _format_widget_ids(screen_info)
        base += "\n\n"

    # Tabs
    tabs = screen_info.get("tabs", [])
    if tabs:
        base += f"## Tabs ({len(tabs)})\n{', '.join(tabs)}\n\n"

    # Auto-generated expectations (important for full audit)
    expectations_text = _get_expectations_text(screen_info)
    if expectations_text:
        base += expectations_text
        base += "\n"

    # UX Guidelines and improvement prompts
    guidelines = _get_ux_guidelines(screen_name, "full")
    if guidelines:
        base += guidelines
        base += "\n"

    # Add layout guidelines for full audit
    base += LAYOUT_SIZING_GUIDELINES
    base += "\n"

    base += """## Full Audit Checklist

### Visual Design
- [ ] Layout properly structured (header/content/footer)
- [ ] Elements aligned correctly
- [ ] Consistent spacing between widgets
- [ ] Readable typography with clear hierarchy
- [ ] Good color contrast against dark terminal background
- [ ] Status colors meaningful (green=ok, yellow=warn, red=error)

### Layout & Sizing
- [ ] Content area >=60% of screen height
- [ ] Tables fill available space (not too narrow)
- [ ] No wasted whitespace while content is cramped
- [ ] No text/data truncation

### Data Loading
- [ ] Tables populated with data rows
- [ ] Stats showing actual numbers
- [ ] No stuck loading indicators
- [ ] No empty states when data expected

### Widget Verification
- [ ] All discovered widgets visible in screenshot
- [ ] Interactive elements appear accessible

## Answer Format

Provide scores (1-10) for each category:
VISUAL_SCORE: [score]
LAYOUT_SCORE: [score]
DATA_SCORE: [score]
UX_SCORE: [score]

List issues by severity (CRITICAL > HIGH > MEDIUM > LOW).
For layout/sizing issues, note suspected CSS problems.
Rate overall confidence:
CONFIDENCE: HIGH | MEDIUM | LOW
"""
    return base


def get_analysis_summary(screen_name: str) -> str:
    """Get a brief summary of what to check for a screen.

    Args:
        screen_name: Name of the screen.

    Returns:
        Brief summary string for quick reference.
    """
    screen_info = get_screen_info(screen_name)

    if "error" in screen_info:
        return f"Screen '{screen_name}' not found. Use generic checks."

    docstring = screen_info.get("docstring", "Unknown purpose")
    widget_count = len(screen_info.get("widget_ids", []))
    tabs = screen_info.get("tabs", [])

    summary = f"**{screen_name.upper()}**: {docstring}\n"
    summary += f"Widgets: {widget_count} with IDs"
    if tabs:
        summary += f", Tabs: {len(tabs)}"
    summary += "\n"

    return summary
