"""UX best practices and improvement guidelines.

This module provides UX guidelines that are included in analysis prompts
to help AI identify not just issues but also improvement opportunities.
"""

from __future__ import annotations

from tui_screenshot_capture.constants import (
    IMPROVEMENT_PROMPTS,
    SCREEN_UX_GUIDELINES,
)


def get_guidelines_for_screen(screen_name: str) -> str:
    """Get UX guidelines for a specific screen.

    Args:
        screen_name: Name of the screen.

    Returns:
        Guidelines text.
    """
    return SCREEN_UX_GUIDELINES.get(screen_name, "")


def get_improvement_prompt(analysis_type: str) -> str:
    """Get improvement suggestion prompt for analysis type.

    Args:
        analysis_type: Type of analysis (visual, data, full, etc.).

    Returns:
        Improvement prompt text.
    """
    return IMPROVEMENT_PROMPTS.get(analysis_type, IMPROVEMENT_PROMPTS["standard"])


def get_full_guidelines(screen_name: str, analysis_type: str) -> str:
    """Get complete guidelines including screen-specific and improvement prompts.

    Args:
        screen_name: Name of the screen.
        analysis_type: Type of analysis.

    Returns:
        Combined guidelines text.
    """
    parts = []

    # Add screen-specific guidelines
    screen_guidelines = get_guidelines_for_screen(screen_name)
    if screen_guidelines:
        parts.append(screen_guidelines)

    # Add improvement prompt
    improvement_prompt = get_improvement_prompt(analysis_type)
    if improvement_prompt:
        parts.append(improvement_prompt)

    return "\n".join(parts)
