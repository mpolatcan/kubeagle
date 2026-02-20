"""Analysis and optimization models."""

from kubeagle.models.analysis.recommendation import (
    ExtremeLimitRatio,
    Recommendation,
)
from kubeagle.models.analysis.violation import ViolationResult

__all__ = ["ExtremeLimitRatio", "Recommendation", "ViolationResult"]
