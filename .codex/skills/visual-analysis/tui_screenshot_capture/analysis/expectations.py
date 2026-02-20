"""Auto-generate expectations from screen code analysis.

This module analyzes widget definitions to infer expected states:
- Default values that should change after data loads
- Loading indicators that should hide
- Data widgets that should have content
- Status indicators with expected states
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from tui_screenshot_capture.constants import (
    CSS_STATE_PATTERNS,
    EXPECTATION_LOADING_REGEX,
    WIDGET_ID_PATTERNS,
    WIDGET_TYPE_EXPECTATIONS,
)


class ExpectationType(str, Enum):
    """Types of expectations for widgets."""

    SHOULD_HAVE_DATA = "should_have_data"  # DataTable, ListView should have rows
    SHOULD_HIDE = "should_hide"  # Loading indicators should disappear
    SHOULD_CHANGE = "should_change"  # Default values should update
    SHOULD_SHOW_NUMBER = "should_show_number"  # Stats should show numbers
    SHOULD_SHOW_STATUS = "should_show_status"  # Status widgets with states
    SHOULD_BE_INTERACTIVE = "should_be_interactive"  # Buttons, inputs


@dataclass(slots=True)
class WidgetExpectation:
    """Expected state for a widget."""

    widget_id: str
    widget_type: str
    expectation_type: ExpectationType
    description: str
    default_value: str | None = None
    expected_values: list[str] = field(default_factory=list)
    css_states: list[str] = field(default_factory=list)
    severity: str = "MEDIUM"  # CRITICAL, HIGH, MEDIUM, LOW


def _str_to_expectation_type(value: str) -> ExpectationType | None:
    """Convert a string value to ExpectationType enum.

    Args:
        value: String value matching an ExpectationType member value.

    Returns:
        ExpectationType or None if value doesn't match.
    """
    try:
        return ExpectationType(value)
    except ValueError:
        return None


def infer_expectation_from_id(widget_id: str) -> ExpectationType | None:
    """Infer expectation type from widget ID naming pattern.

    Args:
        widget_id: The widget's ID.

    Returns:
        ExpectationType or None if no pattern matches.
    """
    widget_id_lower = widget_id.lower()
    for pattern, exp_type_str in WIDGET_ID_PATTERNS.items():
        if re.search(pattern, widget_id_lower):
            return _str_to_expectation_type(exp_type_str)
    return None


def is_loading_text(text: str) -> bool:
    """Check if text indicates a loading/placeholder state.

    Uses pre-compiled regex for performance.

    Args:
        text: The text content to check.

    Returns:
        True if text appears to be a loading indicator.
    """
    text_lower = text.lower().strip()
    return bool(EXPECTATION_LOADING_REGEX.match(text_lower))


def extract_css_states(classes: list[str]) -> list[str]:
    """Extract expected states from CSS classes.

    Args:
        classes: List of CSS class names.

    Returns:
        List of expected state names.
    """
    states: list[str] = []
    for css_class in classes:
        css_lower = css_class.lower()
        for pattern, state_name in CSS_STATE_PATTERNS.items():
            if re.search(pattern, css_lower):
                states.append(state_name)
    return states


def generate_widget_expectation(
    widget_id: str,
    widget_type: str,
    text_content: str | None = None,
    css_classes: list[str] | None = None,
) -> WidgetExpectation | None:
    """Generate expectation for a single widget.

    Args:
        widget_id: Widget's ID.
        widget_type: Widget's type (e.g., "Static", "DataTable").
        text_content: Default text content if any.
        css_classes: CSS classes applied to widget.

    Returns:
        WidgetExpectation or None if no expectation applies.
    """
    css_classes = css_classes or []

    # Try to infer from widget type first
    exp_type_str = WIDGET_TYPE_EXPECTATIONS.get(widget_type)
    exp_type = _str_to_expectation_type(exp_type_str) if exp_type_str else None

    # Then try ID patterns
    if not exp_type and widget_id:
        exp_type = infer_expectation_from_id(widget_id)

    # Check if default text indicates loading
    if not exp_type and text_content and is_loading_text(text_content):
        exp_type = ExpectationType.SHOULD_CHANGE

    if not exp_type:
        return None

    # Build expectation
    expectation = WidgetExpectation(
        widget_id=widget_id,
        widget_type=widget_type,
        expectation_type=exp_type,
        description=_build_description(exp_type, widget_id, widget_type),
        default_value=text_content,
        css_states=extract_css_states(css_classes),
    )

    # Set severity based on expectation type
    if exp_type == ExpectationType.SHOULD_HIDE:
        expectation.severity = "HIGH"  # Stuck loading is serious
    elif exp_type == ExpectationType.SHOULD_HAVE_DATA:
        expectation.severity = "HIGH"  # Empty tables are serious
    elif exp_type == ExpectationType.SHOULD_SHOW_NUMBER:
        expectation.severity = "MEDIUM"
    else:
        expectation.severity = "LOW"

    return expectation


def _build_description(
    exp_type: ExpectationType, widget_id: str, widget_type: str
) -> str:
    """Build human-readable description for expectation.

    Args:
        exp_type: The expectation type.
        widget_id: Widget's ID.
        widget_type: Widget's type.

    Returns:
        Description string.
    """
    descriptions = {
        ExpectationType.SHOULD_HAVE_DATA: (
            f"{widget_type} '{widget_id}' should have data rows"
        ),
        ExpectationType.SHOULD_HIDE: (
            f"Loading indicator '{widget_id}' should be hidden after data loads"
        ),
        ExpectationType.SHOULD_CHANGE: (
            f"'{widget_id}' should update from default/loading value"
        ),
        ExpectationType.SHOULD_SHOW_NUMBER: (
            f"Stat '{widget_id}' should show a number (not '0' or 'Loading')"
        ),
        ExpectationType.SHOULD_SHOW_STATUS: (
            f"Status '{widget_id}' should show a valid state"
        ),
        ExpectationType.SHOULD_BE_INTERACTIVE: (
            f"{widget_type} '{widget_id}' should be interactive"
        ),
    }
    return descriptions.get(exp_type, f"Check '{widget_id}'")


def generate_screen_expectations(screen_info: dict[str, Any]) -> list[WidgetExpectation]:
    """Generate all expectations for a screen.

    Args:
        screen_info: Screen info from get_screen_info().

    Returns:
        List of WidgetExpectation objects.
    """
    expectations: list[WidgetExpectation] = []
    widgets = screen_info.get("widgets", {})

    for widget_type, items in widgets.items():
        if not isinstance(items, list):
            continue

        for item in items:
            if not isinstance(item, dict):
                continue

            widget_id = item.get("id")
            if not widget_id:
                continue

            text_content = item.get("text")
            css_classes = item.get("classes", [])

            exp = generate_widget_expectation(
                widget_id=widget_id,
                widget_type=widget_type,
                text_content=text_content,
                css_classes=css_classes,
            )

            if exp:
                expectations.append(exp)

    return expectations


def format_expectations_for_prompt(expectations: list[WidgetExpectation]) -> str:
    """Format expectations as text for AI prompt.

    Args:
        expectations: List of expectations.

    Returns:
        Formatted string for inclusion in prompt.
    """
    if not expectations:
        return "No specific expectations defined."

    # Group by severity
    by_severity: dict[str, list[WidgetExpectation]] = {
        "CRITICAL": [],
        "HIGH": [],
        "MEDIUM": [],
        "LOW": [],
    }

    for exp in expectations:
        severity = exp.severity if exp.severity in by_severity else "MEDIUM"
        by_severity[severity].append(exp)

    lines = ["## Expected States (Auto-Generated)\n"]

    for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        exps = by_severity[severity]
        if not exps:
            continue

        lines.append(f"### {severity} Priority\n")
        for exp in exps:
            lines.append(f"- **{exp.widget_id}**: {exp.description}")
            if exp.default_value:
                lines.append(f"  - Default: '{exp.default_value}' (should change)")
            if exp.css_states:
                lines.append(f"  - Valid states: {', '.join(exp.css_states)}")
        lines.append("")

    return "\n".join(lines)


def get_critical_checks(expectations: list[WidgetExpectation]) -> list[str]:
    """Get list of critical checks for quick validation.

    Args:
        expectations: List of expectations.

    Returns:
        List of critical check descriptions.
    """
    checks = []

    # Loading indicators should hide
    loading_exps = [
        e for e in expectations if e.expectation_type == ExpectationType.SHOULD_HIDE
    ]
    if loading_exps:
        ids = [e.widget_id for e in loading_exps]
        checks.append(f"Loading indicators hidden: {', '.join(ids)}")

    # Data tables should have rows
    data_exps = [
        e for e in expectations if e.expectation_type == ExpectationType.SHOULD_HAVE_DATA
    ]
    if data_exps:
        ids = [e.widget_id for e in data_exps]
        checks.append(f"Tables have data: {', '.join(ids)}")

    # Stats should show numbers
    stat_exps = [
        e
        for e in expectations
        if e.expectation_type == ExpectationType.SHOULD_SHOW_NUMBER
    ]
    if stat_exps:
        ids = [e.widget_id for e in stat_exps]
        checks.append(f"Stats show numbers: {', '.join(ids)}")

    return checks
