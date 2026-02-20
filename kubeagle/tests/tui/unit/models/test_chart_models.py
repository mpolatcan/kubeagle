"""Tests for chart info models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from kubeagle.constants.enums import QoSClass
from kubeagle.models.charts.chart_info import ChartInfo, HelmReleaseInfo


class TestChartInfo:
    """Tests for ChartInfo model."""

    def test_chart_info_creation(self) -> None:
        """Test ChartInfo creation with all fields."""
        chart = ChartInfo(
            name="my-chart",
            team="my-team",
            values_file="values.yaml",
            cpu_request=100,
            cpu_limit=200,
            memory_request=128,
            memory_limit=256,
            qos_class=QoSClass.BURSTABLE,
            has_liveness=True,
            has_readiness=True,
            has_startup=False,
            has_anti_affinity=True,
            has_topology_spread=False,
            has_topology=False,
            pdb_enabled=True,
            pdb_template_exists=True,
            pdb_min_available=1,
            pdb_max_unavailable=None,
            replicas=2,
            priority_class=None,
        )

        assert chart.name == "my-chart"
        assert chart.team == "my-team"
        assert chart.cpu_request == 100
        assert chart.qos_class == QoSClass.BURSTABLE
        assert chart.has_liveness is True
        assert chart.pdb_min_available == 1

    def test_chart_info_guaranteed_qos(self) -> None:
        """Test ChartInfo with GUARANTEED QoS."""
        chart = ChartInfo(
            name="my-chart",
            team="my-team",
            values_file="values.yaml",
            cpu_request=500,
            cpu_limit=500,
            memory_request=512,
            memory_limit=512,
            qos_class=QoSClass.GUARANTEED,
            has_liveness=True,
            has_readiness=True,
            has_startup=True,
            has_anti_affinity=True,
            has_topology_spread=True,
            has_topology=True,
            pdb_enabled=True,
            pdb_template_exists=True,
            pdb_min_available=1,
            pdb_max_unavailable=None,
            replicas=3,
            priority_class="critical",
        )

        assert chart.qos_class == QoSClass.GUARANTEED
        assert chart.priority_class == "critical"

    def test_chart_info_minimal(self) -> None:
        """Test ChartInfo with minimal fields."""
        chart = ChartInfo(
            name="my-chart",
            team="my-team",
            values_file="values.yaml",
            cpu_request=0,
            cpu_limit=0,
            memory_request=0,
            memory_limit=0,
            qos_class=QoSClass.BEST_EFFORT,
            has_liveness=False,
            has_readiness=False,
            has_startup=False,
            has_anti_affinity=False,
            has_topology_spread=False,
            has_topology=False,
            pdb_enabled=False,
            pdb_template_exists=False,
            pdb_min_available=None,
            pdb_max_unavailable=None,
            replicas=None,
            priority_class=None,
        )

        assert chart.qos_class == QoSClass.BEST_EFFORT
        assert chart.replicas is None

    def test_chart_info_validation_error(self) -> None:
        """Test ChartInfo raises error for missing required fields."""
        with pytest.raises(ValidationError):
            ChartInfo(  # type: ignore[missing-argument]
                name="my-chart",
                team="my-team",
                # Missing required fields
            )

    def test_chart_info_model_dump(self) -> None:
        """Test ChartInfo can be serialized to dict."""
        chart = ChartInfo(
            name="my-chart",
            team="my-team",
            values_file="values.yaml",
            cpu_request=100,
            cpu_limit=200,
            memory_request=128,
            memory_limit=256,
            qos_class=QoSClass.BURSTABLE,
            has_liveness=True,
            has_readiness=True,
            has_startup=False,
            has_anti_affinity=True,
            has_topology_spread=False,
            has_topology=False,
            pdb_enabled=True,
            pdb_template_exists=True,
            pdb_min_available=1,
            pdb_max_unavailable=None,
            replicas=2,
            priority_class=None,
        )

        data = chart.model_dump()
        assert data["name"] == "my-chart"
        assert data["team"] == "my-team"


class TestHelmReleaseInfo:
    """Tests for HelmReleaseInfo model."""

    def test_helm_release_info_creation(self) -> None:
        """Test HelmReleaseInfo creation."""
        release = HelmReleaseInfo(
            name="frontend",
            namespace="default",
            chart="frontend-1.0.0",
            version="1",
            app_version="1.0.0",
            status="deployed",
        )

        assert release.name == "frontend"
        assert release.namespace == "default"
        assert release.chart == "frontend-1.0.0"
        assert release.version == "1"
        assert release.status == "deployed"

    def test_helm_release_info_model_dump(self) -> None:
        """Test HelmReleaseInfo serialization."""
        release = HelmReleaseInfo(
            name="backend",
            namespace="api",
            chart="backend-2.0.0",
            version="1",
            app_version="2.0.0",
            status="pending-install",
        )

        data = release.model_dump()
        assert data["name"] == "backend"
        assert data["status"] == "pending-install"
