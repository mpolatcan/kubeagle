"""Parse AI vision responses into structured findings.

This module converts freeform AI analysis responses into structured
findings that can be used for PRD creation and issue tracking.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from tui_screenshot_capture.constants import (
    CATEGORY_KEYWORDS,
    RESPONSE_CONFIDENCE_PATTERNS,
    RESPONSE_DATA_STATUS_PATTERNS,
    RESPONSE_LOADING_PATTERNS,
    RESPONSE_SCORE_PATTERNS,
    RESPONSE_STATUS_PATTERNS,
    SEVERITY_KEYWORDS,
)


class FindingSeverity(str, Enum):
    """Severity levels for UX findings."""

    CRITICAL = "CRITICAL"  # Blocks user, data loss risk, crash
    HIGH = "HIGH"  # Major usability issue, broken feature
    MEDIUM = "MEDIUM"  # Noticeable issue, workaround exists
    LOW = "LOW"  # Minor polish, nice-to-have


class FindingCategory(str, Enum):
    """Categories of UX findings."""

    DATA_LOADING = "data_loading"  # Data not loading, stuck, empty
    VISUAL = "visual"  # Layout, alignment, spacing, colors
    LAYOUT_SIZING = "layout_sizing"  # Component sizing, proportions, truncation
    INTERACTION = "interaction"  # Buttons, inputs, navigation
    ACCESSIBILITY = "accessibility"  # Contrast, focus, labels
    PERFORMANCE = "performance"  # Slow, frozen, unresponsive
    CONTENT = "content"  # Text, labels, missing info


@dataclass(slots=True)
class UXFinding:
    """A structured UX finding."""

    title: str
    description: str
    severity: FindingSeverity
    category: FindingCategory
    widget_id: str | None = None
    screen_name: str | None = None
    suggested_fix: str | None = None
    evidence: str | None = None  # Quote from AI response


@dataclass(slots=True)
class AnalysisResult:
    """Structured result from AI analysis."""

    screen_name: str
    status: str  # OK, ISSUES, PASS, FAIL, etc.
    data_loaded: bool | None = None
    loading_visible: bool | None = None
    findings: list[UXFinding] = field(default_factory=list)
    scores: dict[str, int] = field(default_factory=dict)  # visual, data, ux scores
    confidence: str | None = None  # HIGH, MEDIUM, LOW
    summary: str | None = None
    raw_response: str | None = None


# Map severity string keys to FindingSeverity enum
SEVERITY_KEY_MAP: dict[str, FindingSeverity] = {
    "CRITICAL": FindingSeverity.CRITICAL,
    "HIGH": FindingSeverity.HIGH,
    "MEDIUM": FindingSeverity.MEDIUM,
    "LOW": FindingSeverity.LOW,
}

# Map category string keys to FindingCategory enum
CATEGORY_KEY_MAP: dict[str, FindingCategory] = {
    "data_loading": FindingCategory.DATA_LOADING,
    "visual": FindingCategory.VISUAL,
    "layout_sizing": FindingCategory.LAYOUT_SIZING,
    "layout": FindingCategory.LAYOUT_SIZING,  # alias
    "sizing": FindingCategory.LAYOUT_SIZING,  # alias
    "interaction": FindingCategory.INTERACTION,
    "accessibility": FindingCategory.ACCESSIBILITY,
    "performance": FindingCategory.PERFORMANCE,
    "content": FindingCategory.CONTENT,
}


def parse_ai_response(
    response: str,
    screen_name: str,
) -> AnalysisResult:
    """Parse AI vision response into structured result.

    Args:
        response: Raw AI response text.
        screen_name: Name of the analyzed screen.

    Returns:
        AnalysisResult with extracted data.
    """
    result = AnalysisResult(
        screen_name=screen_name,
        status="UNKNOWN",
        raw_response=response,
    )

    # Extract status
    for pattern in RESPONSE_STATUS_PATTERNS:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            result.status = match.group(1).upper()
            break

    # Extract data loading status
    for pattern in RESPONSE_DATA_STATUS_PATTERNS:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            value = match.group(1).upper()
            result.data_loaded = value in ("LOADED", "YES")
            break

    # Extract loading visibility
    for pattern in RESPONSE_LOADING_PATTERNS:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            value = match.group(1).upper()
            result.loading_visible = value in ("YES", "VISIBLE")
            break

    # Extract confidence
    for pattern in RESPONSE_CONFIDENCE_PATTERNS:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            result.confidence = match.group(1).upper()
            break

    # Extract scores
    for score_name, pattern in RESPONSE_SCORE_PATTERNS.items():
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            try:
                result.scores[score_name] = int(match.group(1))
            except ValueError:
                pass

    # Extract summary
    summary_match = re.search(
        r"SUMMARY:\s*(.+?)(?:\n\n|\n[A-Z_]+:|\Z)",
        response,
        re.IGNORECASE | re.DOTALL,
    )
    if summary_match:
        result.summary = summary_match.group(1).strip()

    # Extract findings from ISSUES sections
    result.findings = _extract_findings(response, screen_name)

    return result


def _extract_findings(response: str, screen_name: str) -> list[UXFinding]:
    """Extract individual findings from AI response.

    Args:
        response: Raw AI response.
        screen_name: Screen name for context.

    Returns:
        List of UXFinding objects.
    """
    findings: list[UXFinding] = []

    # Look for issue sections
    issue_sections = [
        r"CRITICAL_ISSUES?:\s*\n(.*?)(?:\n\n|\n[A-Z_]+:|\Z)",
        r"HIGH_ISSUES?:\s*\n(.*?)(?:\n\n|\n[A-Z_]+:|\Z)",
        r"MODERATE_ISSUES?:\s*\n(.*?)(?:\n\n|\n[A-Z_]+:|\Z)",
        r"MINOR_ISSUES?:\s*\n(.*?)(?:\n\n|\n[A-Z_]+:|\Z)",
        r"ISSUES?:\s*\n(.*?)(?:\n\n|\n[A-Z_]+:|\Z)",
        r"MISSING_ELEMENTS?:\s*\n(.*?)(?:\n\n|\n[A-Z_]+:|\Z)",
    ]

    for pattern in issue_sections:
        matches = re.finditer(pattern, response, re.IGNORECASE | re.DOTALL)
        for match in matches:
            section_text = match.group(1)
            severity = _infer_severity_from_section(pattern)

            # Parse individual issues (bullet points)
            issue_lines = re.findall(r"[-*]\s*(.+?)(?:\n|$)", section_text)
            for line in issue_lines:
                if line.strip():
                    finding = _parse_issue_line(line, severity, screen_name)
                    if finding:
                        findings.append(finding)

    # Also look for inline issues
    inline_patterns = [
        r"\[CRITICAL\]\s*(.+?)(?:\n|$)",
        r"\[HIGH\]\s*(.+?)(?:\n|$)",
        r"\[MEDIUM\]\s*(.+?)(?:\n|$)",
        r"\[LOW\]\s*(.+?)(?:\n|$)",
    ]

    for pattern in inline_patterns:
        severity = _infer_severity_from_section(pattern)
        matches = re.finditer(pattern, response, re.IGNORECASE)
        for match in matches:
            finding = _parse_issue_line(match.group(1), severity, screen_name)
            if finding:
                findings.append(finding)

    return findings


def _infer_severity_from_section(pattern: str) -> FindingSeverity:
    """Infer severity from section pattern.

    Args:
        pattern: Regex pattern that matched.

    Returns:
        Inferred severity level.
    """
    pattern_lower = pattern.lower()
    if "critical" in pattern_lower:
        return FindingSeverity.CRITICAL
    elif "high" in pattern_lower:
        return FindingSeverity.HIGH
    elif "moderate" in pattern_lower or "medium" in pattern_lower:
        return FindingSeverity.MEDIUM
    elif "minor" in pattern_lower or "low" in pattern_lower:
        return FindingSeverity.LOW
    else:
        return FindingSeverity.MEDIUM  # Default


def _parse_issue_line(
    line: str,
    default_severity: FindingSeverity,
    screen_name: str,
) -> UXFinding | None:
    """Parse a single issue line into a finding.

    Args:
        line: Issue description text.
        default_severity: Default severity if not specified.
        screen_name: Screen name for context.

    Returns:
        UXFinding or None if line is empty/invalid.
    """
    line = line.strip()
    if not line or len(line) < 5:
        return None

    # Extract widget ID if mentioned (CSS selector #id or quoted 'id')
    widget_id = None
    id_match = re.search(r"#([a-z][-a-z0-9_]+)\b|'([a-z][-a-z0-9_]+)'", line, re.IGNORECASE)
    if id_match:
        widget_id = id_match.group(1) or id_match.group(2)

    # Infer severity from text (using frozenset for O(1) substring check)
    severity: FindingSeverity = default_severity
    line_lower = line.lower()
    for sev_key, keywords in SEVERITY_KEYWORDS.items():
        if any(kw in line_lower for kw in keywords):
            severity = SEVERITY_KEY_MAP.get(sev_key, default_severity)
            break

    # Infer category from text (using frozenset for O(1) substring check)
    category: FindingCategory = FindingCategory.VISUAL  # Default
    for cat_key, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in line_lower for kw in keywords):
            category = CATEGORY_KEY_MAP.get(cat_key, FindingCategory.VISUAL)
            break

    # Generate title (first sentence or truncated)
    title = line.split(".")[0][:80]
    if len(line) > 80 and "." not in line[:80]:
        title = line[:77] + "..."

    return UXFinding(
        title=title,
        description=line,
        severity=severity,
        category=category,
        widget_id=widget_id,
        screen_name=screen_name,
        evidence=line,
    )


def format_findings_for_prd(findings: list[UXFinding]) -> str:
    """Format findings for PRD inclusion.

    Args:
        findings: List of findings to format.

    Returns:
        Markdown-formatted string for PRD.
    """
    if not findings:
        return "No issues found."

    # Group by severity
    by_severity: dict[FindingSeverity, list[UXFinding]] = {
        FindingSeverity.CRITICAL: [],
        FindingSeverity.HIGH: [],
        FindingSeverity.MEDIUM: [],
        FindingSeverity.LOW: [],
    }

    for finding in findings:
        by_severity[finding.severity].append(finding)

    lines = ["## UX Findings\n"]

    for severity in [
        FindingSeverity.CRITICAL,
        FindingSeverity.HIGH,
        FindingSeverity.MEDIUM,
        FindingSeverity.LOW,
    ]:
        items = by_severity[severity]
        if not items:
            continue

        lines.append(f"### {severity.value} ({len(items)})\n")

        for finding in items:
            lines.append(f"- **{finding.title}**")
            if finding.widget_id:
                lines.append(f"  - Widget: `#{finding.widget_id}`")
            lines.append(f"  - Category: {finding.category.value}")
            if finding.suggested_fix:
                lines.append(f"  - Fix: {finding.suggested_fix}")
            lines.append("")

    return "\n".join(lines)


def format_findings_for_task(
    findings: list[UXFinding],
    screen_name: str,
) -> str:
    """Format findings as actionable tasks.

    Args:
        findings: List of findings.
        screen_name: Screen name.

    Returns:
        Markdown task list.
    """
    if not findings:
        return "No tasks needed."

    lines = [f"## Tasks for {screen_name.upper()} Screen\n"]

    # Sort by severity
    severity_order = list(FindingSeverity)
    sorted_findings = sorted(
        findings,
        key=lambda f: severity_order.index(f.severity),
    )

    for finding in sorted_findings:
        severity_badge = f"[{finding.severity.value}]"
        lines.append(f"- [ ] {severity_badge} {finding.title}")
        if finding.widget_id:
            lines.append(f"      Widget: `#{finding.widget_id}`")
        lines.append("")

    return "\n".join(lines)


def get_summary_stats(result: AnalysisResult) -> dict[str, Any]:
    """Get summary statistics from analysis result.

    Args:
        result: Analysis result.

    Returns:
        Dict with summary stats.
    """
    findings = result.findings

    return {
        "screen": result.screen_name,
        "status": result.status,
        "data_loaded": result.data_loaded,
        "loading_visible": result.loading_visible,
        "confidence": result.confidence,
        "total_findings": len(findings),
        "by_severity": {
            "critical": sum(1 for f in findings if f.severity == FindingSeverity.CRITICAL),
            "high": sum(1 for f in findings if f.severity == FindingSeverity.HIGH),
            "medium": sum(1 for f in findings if f.severity == FindingSeverity.MEDIUM),
            "low": sum(1 for f in findings if f.severity == FindingSeverity.LOW),
        },
        "by_category": {
            cat.value: count
            for cat in FindingCategory
            if (count := sum(1 for f in findings if f.category == cat)) > 0
        },
        "scores": result.scores,
        "summary": result.summary,
    }
