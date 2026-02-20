"""Tests for report models."""

from __future__ import annotations

from kubeagle.models.reports.report_data import ReportData


class TestReportData:
    """Tests for ReportData model."""

    def test_report_data_creation(self) -> None:
        """Test ReportData creation."""
        report = ReportData(
            nodes=[],
            event_summary=None,
            pdbs=[],
            single_replica_workloads=[],
            charts=[],
            violations=[],
            cluster_name="my-cluster",
            context="my-context",
            timestamp="2024-01-15T10:30:00Z",
        )

        assert report.cluster_name == "my-cluster"
        assert report.charts == []
        assert report.violations == []
