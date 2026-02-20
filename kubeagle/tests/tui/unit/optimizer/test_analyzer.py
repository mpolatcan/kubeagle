"""Tests for chart analyzer."""

from __future__ import annotations

from kubeagle.models.optimization.optimization_rule import (
    OptimizationRule,
)
from kubeagle.optimizer.analyzer import ChartAnalyzer


class TestChartAnalyzer:
    """Tests for ChartAnalyzer class."""

    def test_analyzer_init_default_rules(self) -> None:
        """Test ChartAnalyzer initialization with default rules."""
        analyzer = ChartAnalyzer()
        assert len(analyzer.rules) > 0

    def test_analyzer_init_custom_rules(self) -> None:
        """Test ChartAnalyzer initialization with custom rules."""
        custom_rules = [
            OptimizationRule(
                id="CUSTOM001",
                name="Custom Rule",
                description="Custom rule for testing",
                category="test",
                severity="warning",
                check=lambda x: [],
            )
        ]
        analyzer = ChartAnalyzer(rules=custom_rules)
        assert len(analyzer.rules) == 1
        assert analyzer.rules[0].id == "CUSTOM001"


class TestOptimizationRule:
    """Tests for OptimizationRule."""

    def test_rule_creation(self) -> None:
        """Test rule creation."""
        rule = OptimizationRule(
            id="TEST001",
            name="Test Rule",
            description="Test description",
            category="test",
            severity="warning",
            check=lambda x: [],
        )

        assert rule.id == "TEST001"
        assert rule.name == "Test Rule"

    def test_rule_check_returns_empty(self) -> None:
        """Test rule check returns empty list."""
        rule = OptimizationRule(
            id="TEST002",
            name="Test Rule",
            description="Test description",
            category="test",
            severity="warning",
            check=lambda x: [],
        )

        result = rule.check({})
        assert result == []
