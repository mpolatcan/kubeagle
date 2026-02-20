"""Optimization rule models."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

if TYPE_CHECKING:
    from kubeagle.models.optimization.optimization_violation import (
        OptimizationViolation,
    )


class OptimizationRule(BaseModel):
    """Definition of an optimization rule."""

    id: str
    name: str
    description: str
    severity: str
    category: str
    check: Callable[[dict], list[OptimizationViolation]]
    fix: Callable[[dict, OptimizationViolation], dict[str, Any] | None] = (
        lambda *_: None
    )
    auto_fixable: bool = False
