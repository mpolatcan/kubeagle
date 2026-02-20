"""Chart analyzer for detecting optimization violations."""

import logging

from kubeagle.optimizer.rules import (
    RULES,
    OptimizationRule,
    OptimizationViolation,
)

logger = logging.getLogger(__name__)


class ChartAnalyzer:
    """Analyzes Helm chart values for optimization violations."""

    def __init__(self, rules: list[OptimizationRule] | None = None) -> None:
        """Initialize the analyzer with optional custom rules."""
        self.rules = rules or RULES

    def analyze(self, chart_data: dict) -> list[OptimizationViolation]:
        """Analyze a chart for optimization violations.

        Args:
            chart_data: Dictionary containing chart values (from values.yaml)

        Returns:
            List of OptimizationViolation for each detected issue
        """
        violations: list[OptimizationViolation] = []
        for rule in self.rules:
            violations.extend(self._check_rule_safely(rule, chart_data))
        return violations

    @staticmethod
    def _check_rule_safely(
        rule: OptimizationRule,
        chart_data: dict,
    ) -> list[OptimizationViolation]:
        """Run a single rule and convert failures into log entries."""
        try:
            return rule.check(chart_data)
        except Exception as e:
            logger.warning(
                "Rule %s failed with error: %s", rule.id, e, exc_info=True
            )
            return []
