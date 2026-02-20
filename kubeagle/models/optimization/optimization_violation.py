"""Optimization violation models."""

from typing import Any

from pydantic import BaseModel


class OptimizationViolation(BaseModel):
    """Represents a violation of an optimization rule."""

    rule_id: str
    name: str
    description: str
    severity: str  # error, warning, info
    category: str
    fix_preview: dict[str, Any] | None = None
    auto_fixable: bool = False
