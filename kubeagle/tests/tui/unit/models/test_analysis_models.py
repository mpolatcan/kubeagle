"""Tests for analysis models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from kubeagle.constants.enums import Severity
from kubeagle.models.analysis.recommendation import ExtremeLimitRatio
from kubeagle.models.analysis.violation import ViolationResult


class TestViolationResult:
    """Tests for ViolationResult model."""

    def test_violation_result_creation(self) -> None:
        """Test ViolationResult creation."""
        violation = ViolationResult(
            id="RES005",
            chart_name="my-chart",
            rule_name="High CPU Limit/Request Ratio",
            rule_id="RES005",
            category="resources",
            severity=Severity.WARNING,
            description="CPU limit is 5x the request",
            current_value="500m",
            recommended_value="200m",
            fix_available=True,
        )

        assert violation.id == "RES005"
        assert violation.chart_name == "my-chart"
        assert violation.category == "resources"
        assert violation.severity == Severity.WARNING
        assert violation.fix_available is True
        assert violation.analysis_source == "values"
        assert violation.fix_verification_status == "not_run"
        assert violation.wiring_suggestions == []

    def test_violation_result_error_severity(self) -> None:
        """Test ViolationResult with ERROR severity."""
        violation = ViolationResult(
            id="PRB001",
            chart_name="my-chart",
            rule_name="Missing Liveness Probe",
            rule_id="PRB001",
            category="probes",
            severity=Severity.ERROR,
            description="Container has no liveness probe",
            current_value="Not configured",
            recommended_value="Add liveness probe",
            fix_available=True,
        )

        assert violation.severity == Severity.ERROR

    def test_violation_result_info_severity(self) -> None:
        """Test ViolationResult with INFO severity."""
        violation = ViolationResult(
            id="AVL002",
            chart_name="my-chart",
            rule_name="No Pod Anti-Affinity",
            rule_id="AVL002",
            category="availability",
            severity=Severity.INFO,
            description="Multi-replica deployment has no anti-affinity",
            current_value="No anti-affinity configured",
            recommended_value="Add pod anti-affinity",
            fix_available=False,
        )

        assert violation.severity == Severity.INFO
        assert violation.fix_available is False

    def test_violation_result_serialization(self) -> None:
        """Test ViolationResult can be serialized."""
        violation = ViolationResult(
            id="RES005",
            chart_name="my-chart",
            rule_name="High CPU Limit/Request Ratio",
            rule_id="RES005",
            category="resources",
            severity=Severity.WARNING,
            description="CPU limit is 5x the request",
            current_value="500m",
            recommended_value="200m",
            fix_available=True,
        )

        data = violation.model_dump()
        assert data["id"] == "RES005"
        assert data["severity"] == Severity.WARNING

    def test_violation_result_validation_error(self) -> None:
        """Test ViolationResult raises error for missing required fields."""
        with pytest.raises(ValidationError):
            ViolationResult(  # type: ignore[missing-argument]
                id="RES005",
                chart_name="my-chart",
                # Missing required fields
            )


class TestExtremeLimitRatio:
    """Tests for ExtremeLimitRatio model."""

    def test_extreme_limit_ratio_creation(self) -> None:
        """Test ExtremeLimitRatio creation."""
        ratio = ExtremeLimitRatio(
            chart_name="my-chart",
            team="my-team",
            cpu_request=100,
            cpu_limit=500,
            cpu_ratio=5.0,
            memory_request=128,
            memory_limit=512,
            memory_ratio=4.0,
            max_ratio=5.0,
        )

        assert ratio.chart_name == "my-chart"
        assert ratio.team == "my-team"
        assert ratio.cpu_ratio == 5.0
        assert ratio.max_ratio == 5.0

    def test_extreme_limit_ratio_sorting(self) -> None:
        """Test ExtremeLimitRatio sorting by max_ratio."""
        ratios = [
            ExtremeLimitRatio(
                chart_name="chart1",
                team="team-a",
                cpu_request=100,
                cpu_limit=300,
                cpu_ratio=3.0,
                memory_request=128,
                memory_limit=256,
                memory_ratio=2.0,
                max_ratio=3.0,
            ),
            ExtremeLimitRatio(
                chart_name="chart2",
                team="team-b",
                cpu_request=100,
                cpu_limit=500,
                cpu_ratio=5.0,
                memory_request=128,
                memory_limit=512,
                memory_ratio=4.0,
                max_ratio=5.0,
            ),
        ]

        sorted_ratios = sorted(ratios, key=lambda x: x.max_ratio, reverse=True)
        assert sorted_ratios[0].chart_name == "chart2"

    def test_extreme_limit_ratio_serialization(self) -> None:
        """Test ExtremeLimitRatio serialization."""
        ratio = ExtremeLimitRatio(
            chart_name="my-chart",
            team="my-team",
            cpu_request=100,
            cpu_limit=500,
            cpu_ratio=5.0,
            memory_request=128,
            memory_limit=512,
            memory_ratio=4.0,
            max_ratio=5.0,
        )

        data = ratio.model_dump()
        assert data["chart_name"] == "my-chart"
        assert data["max_ratio"] == 5.0
