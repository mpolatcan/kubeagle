"""Analysis module for AI-powered screenshot analysis.

This module provides:
- Dynamic widget discovery from screen code
- Auto-generated expectations for widgets
- Contextual prompt generation for AI vision
- Response parsing for structured findings
- UX guidelines and improvement suggestions
"""

from tui_screenshot_capture.analysis.expectations import (
    ExpectationType,
    WidgetExpectation,
    format_expectations_for_prompt,
    generate_screen_expectations,
    generate_widget_expectation,
    get_critical_checks,
)
from tui_screenshot_capture.analysis.prompt_generator import (
    AnalysisType,
    generate_analysis_prompt,
    get_analysis_summary,
    get_screen_info,
)
from tui_screenshot_capture.analysis.response_parser import (
    AnalysisResult,
    FindingCategory,
    FindingSeverity,
    UXFinding,
    format_findings_for_prd,
    format_findings_for_task,
    get_summary_stats,
    parse_ai_response,
)
from tui_screenshot_capture.analysis.ux_guidelines import (
    get_full_guidelines,
    get_guidelines_for_screen,
    get_improvement_prompt,
)

__all__ = [
    # Prompt generation
    "AnalysisType",
    "generate_analysis_prompt",
    "get_analysis_summary",
    "get_screen_info",
    # Expectations
    "ExpectationType",
    "WidgetExpectation",
    "format_expectations_for_prompt",
    "generate_screen_expectations",
    "generate_widget_expectation",
    "get_critical_checks",
    # Response parsing
    "AnalysisResult",
    "FindingCategory",
    "FindingSeverity",
    "UXFinding",
    "format_findings_for_prd",
    "format_findings_for_task",
    "get_summary_stats",
    "parse_ai_response",
    # UX Guidelines
    "get_full_guidelines",
    "get_guidelines_for_screen",
    "get_improvement_prompt",
]
