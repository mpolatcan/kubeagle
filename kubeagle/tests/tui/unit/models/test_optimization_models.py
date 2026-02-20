"""Tests for optimization models."""

from __future__ import annotations

from kubeagle.models.optimization.optimization_rule import (
    OptimizationRule,
)
from kubeagle.models.optimization.optimization_violation import (
    OptimizationViolation,
)


class TestOptimizationRule:
    """Tests for OptimizationRule model."""

    def test_optimization_rule_creation(self) -> None:
        """Test OptimizationRule creation."""
        rule = OptimizationRule(
            id="RES001",
            name="Test Rule",
            description="Test description",
            category="resources",
            severity="warning",
            check=lambda x: [],
        )

        assert rule.id == "RES001"
        assert rule.name == "Test Rule"
        assert rule.category == "resources"


class TestOptimizationViolation:
    """Tests for OptimizationViolation model."""

    def test_optimization_violation_creation(self) -> None:
        """Test OptimizationViolation creation."""
        violation = OptimizationViolation(
            rule_id="RES005",
            name="High CPU Limit/Request Ratio",
            description="CPU limit is 5x the request",
            category="resources",
            severity="warning",
            fix_preview={"resources": {"limits": {"cpu": "200m"}}},
            auto_fixable=True,
        )

        assert violation.rule_id == "RES005"
        assert violation.category == "resources"
        assert violation.auto_fixable is True
