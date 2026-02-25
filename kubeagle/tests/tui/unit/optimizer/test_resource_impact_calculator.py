"""Unit tests for ResourceImpactCalculator."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from kubeagle.constants.enums import QoSClass
from kubeagle.constants.instance_types import HOURS_PER_MONTH, SPOT_PRICES
from kubeagle.models.charts.chart_info import ChartInfo
from kubeagle.optimizer.resource_impact_calculator import (
    IMPACT_RULE_IDS,
    REPLICA_RULE_IDS,
    RESOURCE_RULE_IDS,
    ResourceImpactCalculator,
    _build_instance_types,
)
from kubeagle.optimizer.rules import configure_rule_thresholds


@pytest.fixture(autouse=True)
def _clear_fixed_resource_fields():
    """Ensure tests run without fixed resource field restrictions."""
    configure_rule_thresholds(fixed_resource_fields=set())
    yield
    configure_rule_thresholds(fixed_resource_fields=set())


def _make_chart(
    name: str = "test-chart",
    team: str = "platform",
    cpu_request: float = 100.0,
    cpu_limit: float = 500.0,
    memory_request: float = 128 * 1024**2,
    memory_limit: float = 512 * 1024**2,
    replicas: int = 2,
    values_file: str = "values.yaml",
) -> ChartInfo:
    """Create a minimal ChartInfo for testing."""
    return ChartInfo(
        name=name,
        team=team,
        values_file=values_file,
        cpu_request=cpu_request,
        cpu_limit=cpu_limit,
        memory_request=memory_request,
        memory_limit=memory_limit,
        qos_class=QoSClass.BURSTABLE,
        has_liveness=True,
        has_readiness=True,
        has_startup=False,
        has_anti_affinity=False,
        has_topology_spread=False,
        has_topology=False,
        pdb_enabled=False,
        pdb_template_exists=False,
        pdb_min_available=None,
        pdb_max_unavailable=None,
        replicas=replicas,
        priority_class=None,
    )


def _make_violation(
    rule_id: str = "RES005",
    chart_name: str = "test-chart",
    parent_chart: str | None = None,
) -> MagicMock:
    """Create a mock violation."""
    v = MagicMock()
    v.id = rule_id
    v.rule_id = rule_id
    v.chart_name = chart_name
    v.parent_chart = parent_chart
    v.rule_name = f"Rule {rule_id}"
    v.description = f"Description for {rule_id}"
    v.severity = MagicMock()
    v.severity.value = "warning"
    v.current_value = "current"
    v.recommended_value = "recommended"
    v.fix_available = True
    return v


class TestBuildInstanceTypes:
    def test_default_types(self) -> None:
        specs = _build_instance_types()
        assert len(specs) == 6
        assert specs[0].name == "m5.large"
        assert specs[0].vcpus == 2
        assert specs[0].cpu_millicores == 2000
        assert specs[0].memory_bytes == int(8.0 * 1024**3)
        assert specs[0].spot_price_usd == 0.035

    def test_custom_types(self) -> None:
        custom = [("c5.large", 2, 4.0, 0.085, 0.031)]
        specs = _build_instance_types(custom)
        assert len(specs) == 1
        assert specs[0].name == "c5.large"
        assert specs[0].memory_gib == 4.0
        assert specs[0].spot_price_usd == 0.031


class TestResourceImpactCalculatorNoViolations:
    def test_no_violations_before_equals_after(self) -> None:
        calc = ResourceImpactCalculator()
        chart = _make_chart()
        result = calc.compute_impact([chart], [])

        assert result.before.cpu_request_total == result.after.cpu_request_total
        assert result.before.cpu_limit_total == result.after.cpu_limit_total
        assert result.before.memory_request_total == result.after.memory_request_total
        assert result.before.memory_limit_total == result.after.memory_limit_total
        assert result.delta.cpu_request_diff == 0.0
        assert result.delta.cpu_limit_diff == 0.0
        assert result.delta.replicas_diff == 0

    def test_empty_charts(self) -> None:
        calc = ResourceImpactCalculator()
        result = calc.compute_impact([], [])

        assert result.before.chart_count == 0
        assert result.after.chart_count == 0
        assert result.before.total_replicas == 0


class TestResourceImpactCalculatorWithViolations:
    def test_res005_increases_cpu_request(self) -> None:
        """RES005 (high CPU ratio) should increase request, never decrease limit."""
        chart = _make_chart(cpu_request=100.0, cpu_limit=1000.0, replicas=1)
        violation = _make_violation("RES005", "test-chart")
        calc = ResourceImpactCalculator()

        result = calc.compute_impact([chart], [violation])

        # After: request increased to limit/1.5, limit unchanged
        assert result.after.cpu_request_total > result.before.cpu_request_total
        assert result.after.cpu_limit_total == result.before.cpu_limit_total
        assert result.delta.cpu_limit_diff == 0

    def test_res004_adds_requests(self) -> None:
        """RES004 (no requests) should add CPU+memory requests."""
        chart = _make_chart(
            cpu_request=0.0, cpu_limit=0.0,
            memory_request=0.0, memory_limit=0.0,
            replicas=1,
        )
        violation = _make_violation("RES004", "test-chart")
        calc = ResourceImpactCalculator()

        result = calc.compute_impact([chart], [violation])

        # After should have non-zero requests
        assert result.after.cpu_request_total > 0
        assert result.after.memory_request_total > 0

    def test_avl005_doubles_replicas(self) -> None:
        """AVL005 (single replica) should increase to 2 replicas."""
        chart = _make_chart(replicas=1, cpu_request=100.0, cpu_limit=200.0)
        violation = _make_violation("AVL005", "test-chart")
        calc = ResourceImpactCalculator()

        result = calc.compute_impact([chart], [violation])

        # After should have 2 replicas, doubling total resources
        assert result.after.total_replicas == 2
        assert result.after.cpu_request_total == pytest.approx(
            result.before.cpu_request_total * 2
        )
        assert result.delta.replicas_diff == 1

    def test_res002_adds_cpu_limit(self) -> None:
        """RES002 (no CPU limit) should add CPU limit."""
        chart = _make_chart(cpu_request=200.0, cpu_limit=0.0, replicas=1)
        violation = _make_violation("RES002", "test-chart")
        calc = ResourceImpactCalculator()

        result = calc.compute_impact([chart], [violation])

        # After should have a CPU limit set
        assert result.after.cpu_limit_total > 0

    def test_res007_bumps_low_cpu(self) -> None:
        """RES007 (very low CPU) should bump to 100m."""
        chart = _make_chart(cpu_request=10.0, replicas=1)
        violation = _make_violation("RES007", "test-chart")
        calc = ResourceImpactCalculator()

        result = calc.compute_impact([chart], [violation])

        assert result.after.cpu_request_total >= 100.0


class TestFleetAggregation:
    def test_fleet_sums_correctly(self) -> None:
        """Multiple charts should sum resource totals."""
        chart1 = _make_chart(name="chart-1", cpu_request=100.0, replicas=2)
        chart2 = _make_chart(name="chart-2", cpu_request=200.0, replicas=3)
        calc = ResourceImpactCalculator()

        result = calc.compute_impact([chart1, chart2], [])

        expected_cpu_req = (100.0 * 2) + (200.0 * 3)
        assert result.before.cpu_request_total == pytest.approx(expected_cpu_req)
        assert result.before.chart_count == 2
        assert result.before.total_replicas == 5


class TestNodeEstimation:
    def test_cpu_bound_scenario(self) -> None:
        """Node count should be driven by CPU when CPU is the bottleneck."""
        chart = _make_chart(
            cpu_request=2000.0,  # 2 cores per replica
            memory_request=256 * 1024**2,  # 256Mi per replica
            replicas=10,
        )
        calc = ResourceImpactCalculator()
        result = calc.compute_impact(
            [chart], [],
            instance_types=[("m5.large", 2, 8.0, 0.096, 0.035)],
        )

        assert len(result.node_estimations) == 1
        est = result.node_estimations[0]
        # 20000m CPU total / (2000 * 0.92 * 0.85) usable = ~13 nodes
        assert est.nodes_before > 1
        assert est.spot_price_usd == 0.035

    def test_memory_bound_scenario(self) -> None:
        """Node count should be driven by memory when memory is the bottleneck."""
        chart = _make_chart(
            cpu_request=50.0,  # very low CPU
            memory_request=4 * 1024**3,  # 4Gi per replica
            replicas=10,
        )
        calc = ResourceImpactCalculator()
        result = calc.compute_impact(
            [chart], [],
            instance_types=[("m5.large", 2, 8.0, 0.096, 0.035)],
        )

        assert len(result.node_estimations) == 1
        est = result.node_estimations[0]
        # Memory-heavy workload should need many nodes
        assert est.nodes_before > 1

    def test_minimum_one_node(self) -> None:
        """Node estimation should never drop below 1."""
        chart = _make_chart(
            cpu_request=1.0,
            memory_request=1024.0,
            replicas=1,
        )
        calc = ResourceImpactCalculator()
        result = calc.compute_impact(
            [chart], [],
            instance_types=[("m5.xlarge", 4, 16.0, 0.192, 0.067)],
        )

        est = result.node_estimations[0]
        assert est.nodes_before >= 1
        assert est.nodes_after >= 1


class TestResourceDelta:
    def test_percentage_calculation(self) -> None:
        calc = ResourceImpactCalculator()
        chart = _make_chart(cpu_request=100.0, cpu_limit=1000.0, replicas=1)
        violation = _make_violation("RES005", "test-chart")

        result = calc.compute_impact([chart], [violation])

        # RES005 increases request, limit stays unchanged
        assert result.delta.cpu_request_pct > 0
        assert result.delta.cpu_limit_pct == 0

    def test_zero_baseline_no_divide_by_zero(self) -> None:
        """When before is zero, percentage should handle gracefully."""
        chart = _make_chart(
            cpu_request=0.0, cpu_limit=0.0,
            memory_request=0.0, memory_limit=0.0,
            replicas=1,
        )
        violation = _make_violation("RES004", "test-chart")
        calc = ResourceImpactCalculator()

        result = calc.compute_impact([chart], [violation])

        # Should not raise; percentage for 0->positive is 100%
        assert result.delta.cpu_request_pct == 100.0


class TestRuleIdConstants:
    def test_resource_rule_ids(self) -> None:
        assert "RES002" in RESOURCE_RULE_IDS
        assert "RES009" in RESOURCE_RULE_IDS
        assert "AVL005" not in RESOURCE_RULE_IDS

    def test_replica_rule_ids(self) -> None:
        assert "AVL005" in REPLICA_RULE_IDS
        assert "RES005" not in REPLICA_RULE_IDS

    def test_impact_rule_ids_is_union(self) -> None:
        assert IMPACT_RULE_IDS == RESOURCE_RULE_IDS | REPLICA_RULE_IDS


class TestWithOptimizerController:
    def test_uses_controller_fix_when_available(self) -> None:
        """When optimizer controller returns a fix, it should be used."""
        chart = _make_chart(cpu_request=100.0, cpu_limit=1000.0, replicas=1)
        violation = _make_violation("RES005", "test-chart")

        controller = MagicMock()
        controller.generate_fix.return_value = {
            "resources": {"limits": {"cpu": "150m"}}
        }

        calc = ResourceImpactCalculator()
        result = calc.compute_impact(
            [chart], [violation], optimizer_controller=controller
        )

        # CPU limit should be 150m (from controller fix)
        assert result.after.cpu_limit_total == pytest.approx(150.0)
        controller.generate_fix.assert_called_once()

    def test_falls_back_when_controller_returns_none(self) -> None:
        """When controller returns None, should use default fix."""
        chart = _make_chart(cpu_request=100.0, cpu_limit=1000.0, replicas=1)
        violation = _make_violation("RES005", "test-chart")

        controller = MagicMock()
        controller.generate_fix.return_value = None

        calc = ResourceImpactCalculator()
        result = calc.compute_impact(
            [chart], [violation], optimizer_controller=controller
        )

        # Default fallback: request increased, limit unchanged
        assert result.after.cpu_request_total > result.before.cpu_request_total
        assert result.after.cpu_limit_total == result.before.cpu_limit_total

    def test_falls_back_when_controller_raises(self) -> None:
        """When controller raises, should use default fix."""
        chart = _make_chart(cpu_request=100.0, cpu_limit=1000.0, replicas=1)
        violation = _make_violation("RES005", "test-chart")

        controller = MagicMock()
        controller.generate_fix.side_effect = RuntimeError("fail")

        calc = ResourceImpactCalculator()
        result = calc.compute_impact(
            [chart], [violation], optimizer_controller=controller
        )

        assert result.after.cpu_request_total > result.before.cpu_request_total
        assert result.after.cpu_limit_total == result.before.cpu_limit_total


class TestNonResourceViolationsIgnored:
    def test_probe_violations_not_in_impact(self) -> None:
        """PRB violations should not affect resource calculations."""
        chart = _make_chart(replicas=1)
        violation = _make_violation("PRB001", "test-chart")
        calc = ResourceImpactCalculator()

        result = calc.compute_impact([chart], [violation])

        assert result.before.cpu_request_total == result.after.cpu_request_total
        assert result.delta.cpu_request_diff == 0.0


def _make_node(
    instance_type: str = "m5.large",
    cpu_allocatable: float = 1920.0,  # millicores (2 vCPU - system)
    memory_allocatable: float = 7.5 * 1024**3,  # bytes
) -> MagicMock:
    """Create a mock NodeInfo for testing."""
    node = MagicMock()
    node.instance_type = instance_type
    node.cpu_allocatable = cpu_allocatable
    node.memory_allocatable = memory_allocatable
    return node


class TestClusterNodeEstimation:
    def test_cluster_nodes_populated(self) -> None:
        """When cluster_nodes provided, cluster_node_groups should be populated."""
        chart = _make_chart(cpu_request=100.0, replicas=2)
        nodes = [_make_node(), _make_node()]
        calc = ResourceImpactCalculator()

        result = calc.compute_impact([chart], [], cluster_nodes=nodes)

        assert len(result.cluster_node_groups) == 1
        group = result.cluster_node_groups[0]
        assert group.instance_type == "m5.large"
        assert group.node_count == 2

    def test_no_cluster_nodes_empty_groups(self) -> None:
        """When cluster_nodes is None, cluster_node_groups should be empty."""
        chart = _make_chart()
        calc = ResourceImpactCalculator()

        result = calc.compute_impact([chart], [])

        assert result.cluster_node_groups == []

    def test_multiple_instance_types(self) -> None:
        """Nodes of different types should produce separate groups."""
        chart = _make_chart(cpu_request=100.0, replicas=1)
        nodes = [
            _make_node(instance_type="m5.large"),
            _make_node(instance_type="m5.large"),
            _make_node(instance_type="m5.xlarge", cpu_allocatable=3840.0, memory_allocatable=15 * 1024**3),
        ]
        calc = ResourceImpactCalculator()

        result = calc.compute_impact([chart], [], cluster_nodes=nodes)

        assert len(result.cluster_node_groups) == 2
        types = {g.instance_type for g in result.cluster_node_groups}
        assert types == {"m5.large", "m5.xlarge"}

    def test_cluster_node_group_allocatable(self) -> None:
        """Group should have correct per-node and total allocatable values."""
        nodes = [
            _make_node(cpu_allocatable=2000.0, memory_allocatable=8 * 1024**3),
            _make_node(cpu_allocatable=2000.0, memory_allocatable=8 * 1024**3),
        ]
        chart = _make_chart(cpu_request=100.0, replicas=1)
        calc = ResourceImpactCalculator()

        result = calc.compute_impact([chart], [], cluster_nodes=nodes)

        group = result.cluster_node_groups[0]
        assert group.cpu_allocatable_per_node == pytest.approx(2000.0)
        assert group.memory_allocatable_per_node == pytest.approx(8 * 1024**3)
        assert group.cpu_allocatable_total == pytest.approx(4000.0)
        assert group.memory_allocatable_total == pytest.approx(16 * 1024**3)

    def test_cluster_node_minimum_one_needed(self) -> None:
        """Even tiny workloads should need at least 1 node."""
        nodes = [_make_node()]
        chart = _make_chart(cpu_request=1.0, memory_request=1024.0, replicas=1)
        calc = ResourceImpactCalculator()

        result = calc.compute_impact([chart], [], cluster_nodes=nodes)

        group = result.cluster_node_groups[0]
        assert group.nodes_needed_after >= 1

    def test_cluster_node_reduction_calculated(self) -> None:
        """Reduction should be current node count minus nodes needed after."""
        nodes = [_make_node() for _ in range(5)]
        chart = _make_chart(cpu_request=100.0, memory_request=128 * 1024**2, replicas=1)
        calc = ResourceImpactCalculator()

        result = calc.compute_impact([chart], [], cluster_nodes=nodes)

        group = result.cluster_node_groups[0]
        assert group.reduction == group.node_count - group.nodes_needed_after
        assert group.reduction_pct == pytest.approx(
            group.reduction / group.node_count * 100.0
        )


class TestSpotPricing:
    def test_node_estimation_has_spot_cost(self) -> None:
        """Node estimation should include spot cost calculations."""
        chart = _make_chart(cpu_request=2000.0, replicas=5)
        calc = ResourceImpactCalculator()
        result = calc.compute_impact(
            [chart], [],
            instance_types=[("m5.large", 2, 8.0, 0.096, 0.035)],
        )

        est = result.node_estimations[0]
        assert est.spot_price_usd == 0.035
        assert est.cost_before_monthly == pytest.approx(
            est.nodes_before * 0.035 * HOURS_PER_MONTH
        )
        assert est.cost_after_monthly == pytest.approx(
            est.nodes_after * 0.035 * HOURS_PER_MONTH
        )
        assert est.cost_savings_monthly == pytest.approx(
            est.cost_before_monthly - est.cost_after_monthly
        )

    def test_node_estimation_with_request_increase(self) -> None:
        """RES005 increases requests (right-sizing) which may need more nodes."""
        chart = _make_chart(cpu_request=100.0, cpu_limit=1000.0, replicas=10)
        violation = _make_violation("RES005", "test-chart")
        calc = ResourceImpactCalculator()
        result = calc.compute_impact(
            [chart], [violation],
            instance_types=[("m5.large", 2, 8.0, 0.096, 0.035)],
        )

        est = result.node_estimations[0]
        # Request increased → may need more nodes (cost can increase)
        assert est.nodes_after >= est.nodes_before

    def test_cluster_node_spot_price_lookup(self) -> None:
        """Cluster node group should look up spot price from SPOT_PRICES."""
        nodes = [_make_node(instance_type="m5.large") for _ in range(3)]
        chart = _make_chart(cpu_request=100.0, replicas=1)
        calc = ResourceImpactCalculator()

        result = calc.compute_impact([chart], [], cluster_nodes=nodes)

        group = result.cluster_node_groups[0]
        assert group.spot_price_usd == SPOT_PRICES["m5.large"]
        assert group.cost_current_monthly == pytest.approx(
            3 * SPOT_PRICES["m5.large"] * HOURS_PER_MONTH
        )

    def test_cluster_node_unknown_type_zero_price(self) -> None:
        """Unknown instance type should have zero spot price."""
        nodes = [_make_node(instance_type="z99.mega")]
        chart = _make_chart(cpu_request=100.0, replicas=1)
        calc = ResourceImpactCalculator()

        result = calc.compute_impact([chart], [], cluster_nodes=nodes)

        group = result.cluster_node_groups[0]
        assert group.spot_price_usd == 0.0
        assert group.cost_current_monthly == 0.0
        assert group.cost_after_monthly == 0.0

    def test_cluster_node_cost_savings(self) -> None:
        """Cost savings should equal (current - after) nodes * spot * hours."""
        nodes = [_make_node() for _ in range(10)]
        chart = _make_chart(cpu_request=100.0, memory_request=128 * 1024**2, replicas=1)
        calc = ResourceImpactCalculator()

        result = calc.compute_impact([chart], [], cluster_nodes=nodes)

        group = result.cluster_node_groups[0]
        expected_savings = (
            (group.node_count - group.nodes_needed_after)
            * group.spot_price_usd
            * HOURS_PER_MONTH
        )
        assert group.cost_savings_monthly == pytest.approx(expected_savings)

    def test_total_spot_savings_from_cluster(self) -> None:
        """Total savings should sum across all cluster node groups."""
        nodes = [
            _make_node(instance_type="m5.large"),
            _make_node(instance_type="m5.large"),
            _make_node(instance_type="m5.xlarge", cpu_allocatable=3840.0, memory_allocatable=15 * 1024**3),
        ]
        chart = _make_chart(cpu_request=100.0, replicas=1)
        calc = ResourceImpactCalculator()

        result = calc.compute_impact([chart], [], cluster_nodes=nodes)

        expected_total = sum(g.cost_savings_monthly for g in result.cluster_node_groups)
        assert result.total_spot_savings_monthly == pytest.approx(expected_total)

    def test_total_spot_savings_fallback_to_estimations(self) -> None:
        """Without cluster nodes, total savings should come from node estimations."""
        chart = _make_chart(cpu_request=100.0, replicas=1)
        calc = ResourceImpactCalculator()

        result = calc.compute_impact([chart], [])

        expected_total = sum(e.cost_savings_monthly for e in result.node_estimations)
        assert result.total_spot_savings_monthly == pytest.approx(expected_total)

    def test_no_savings_when_no_violations(self) -> None:
        """No violations means before == after, so savings should be zero."""
        chart = _make_chart(cpu_request=100.0, replicas=1)
        calc = ResourceImpactCalculator()
        result = calc.compute_impact(
            [chart], [],
            instance_types=[("m5.large", 2, 8.0, 0.096, 0.035)],
        )

        for est in result.node_estimations:
            assert est.cost_savings_monthly == 0.0
        assert result.total_spot_savings_monthly == 0.0


def _make_cluster_chart(
    name: str = "my-release",
    team: str = "platform",
    namespace: str = "production",
    cpu_request: float = 100.0,
    cpu_limit: float = 500.0,
    memory_request: float = 128 * 1024**2,
    memory_limit: float = 512 * 1024**2,
    replicas: int = 1,
) -> ChartInfo:
    """Create a ChartInfo that simulates a cluster-mode release."""
    return ChartInfo(
        name=name,
        team=team,
        values_file=f"cluster:{namespace}",
        namespace=namespace,
        cpu_request=cpu_request,
        cpu_limit=cpu_limit,
        memory_request=memory_request,
        memory_limit=memory_limit,
        qos_class=QoSClass.BURSTABLE,
        has_liveness=True,
        has_readiness=True,
        has_startup=False,
        has_anti_affinity=False,
        has_topology_spread=False,
        has_topology=False,
        pdb_enabled=False,
        pdb_template_exists=False,
        pdb_min_available=None,
        pdb_max_unavailable=None,
        replicas=replicas,
        priority_class=None,
    )


class TestWorkloadReplicaMap:
    """Tests for actual cluster replica count integration."""

    def test_uses_cluster_replicas_when_map_provided(self) -> None:
        """Cluster replica count should override values-file replicas."""
        chart = _make_cluster_chart(
            name="api-service", namespace="prod", replicas=1,
            cpu_request=100.0,
        )
        replica_map = {("api-service", "prod"): 5}
        calc = ResourceImpactCalculator()

        result = calc.compute_impact(
            [chart], [], workload_replica_map=replica_map,
        )

        # Should use 5 replicas from cluster, not 1 from values
        assert result.before.total_replicas == 5
        assert result.before.cpu_request_total == pytest.approx(100.0 * 5)

    def test_falls_back_to_values_replicas_without_map(self) -> None:
        """Without replica map, values-file replicas should be used."""
        chart = _make_cluster_chart(
            name="api-service", namespace="prod", replicas=3,
            cpu_request=100.0,
        )
        calc = ResourceImpactCalculator()

        result = calc.compute_impact([chart], [])

        assert result.before.total_replicas == 3
        assert result.before.cpu_request_total == pytest.approx(100.0 * 3)

    def test_falls_back_when_chart_not_in_map(self) -> None:
        """Charts not found in the replica map use values-file replicas."""
        chart = _make_cluster_chart(
            name="unknown-release", namespace="prod", replicas=2,
            cpu_request=200.0,
        )
        replica_map = {("api-service", "prod"): 5}
        calc = ResourceImpactCalculator()

        result = calc.compute_impact(
            [chart], [], workload_replica_map=replica_map,
        )

        assert result.before.total_replicas == 2
        assert result.before.cpu_request_total == pytest.approx(200.0 * 2)

    def test_multiple_releases_different_namespaces(self) -> None:
        """Same chart in different namespaces should use their own replica counts."""
        chart_prod = _make_cluster_chart(
            name="api-service", namespace="production", replicas=1,
            cpu_request=100.0,
        )
        chart_staging = _make_cluster_chart(
            name="api-service", namespace="staging", replicas=1,
            cpu_request=100.0,
        )
        replica_map = {
            ("api-service", "production"): 5,
            ("api-service", "staging"): 2,
        }
        calc = ResourceImpactCalculator()

        result = calc.compute_impact(
            [chart_prod, chart_staging], [],
            workload_replica_map=replica_map,
        )

        # 5 + 2 = 7 total replicas
        assert result.before.total_replicas == 7
        assert result.before.cpu_request_total == pytest.approx(100.0 * 7)
        assert result.before.chart_count == 2

    def test_cluster_replicas_also_used_in_after_snapshot(self) -> None:
        """After-optimization snapshot should also use cluster replicas as base."""
        chart = _make_cluster_chart(
            name="api-service", namespace="prod",
            replicas=1, cpu_request=100.0, cpu_limit=1000.0,
        )
        violation = _make_violation("RES005", "api-service")
        replica_map = {("api-service", "prod"): 4}
        calc = ResourceImpactCalculator()

        result = calc.compute_impact(
            [chart], [violation], workload_replica_map=replica_map,
        )

        # Before: 4 replicas * 100m = 400m
        assert result.before.total_replicas == 4
        assert result.before.cpu_request_total == pytest.approx(100.0 * 4)
        # After: 4 replicas * increased_request
        assert result.after.total_replicas == 4
        assert result.after.cpu_request_total > result.before.cpu_request_total

    def test_no_namespace_chart_no_matching_release(self) -> None:
        """Repo-mode chart without matching releases falls back to values replicas."""
        chart = _make_chart(name="local-chart", replicas=2, cpu_request=100.0)
        # Map has a different chart name — no match
        replica_map = {("other-chart", "prod"): 10}
        calc = ResourceImpactCalculator()

        result = calc.compute_impact(
            [chart], [], workload_replica_map=replica_map,
        )

        # Should use values-file replicas (2)
        assert result.before.total_replicas == 2
        assert result.before.cpu_request_total == pytest.approx(100.0 * 2)

    def test_local_chart_aggregates_cluster_releases(self) -> None:
        """Local chart should aggregate replicas from all matching cluster releases."""
        chart = _make_chart(name="honeybadger", replicas=1, cpu_request=100.0)
        # 8 releases across different namespaces, each with 1 replica
        replica_map = {
            ("honeybadger", "ns-1"): 1,
            ("honeybadger", "ns-2"): 1,
            ("honeybadger", "ns-3"): 1,
            ("honeybadger", "ns-4"): 1,
            ("honeybadger", "ns-5"): 1,
            ("honeybadger", "ns-6"): 1,
            ("honeybadger", "ns-7"): 1,
            ("honeybadger", "ns-8"): 1,
        }
        calc = ResourceImpactCalculator()

        result = calc.compute_impact(
            [chart], [], workload_replica_map=replica_map,
        )

        # 8 releases × 1 replica each = 8 total replicas
        assert result.before.total_replicas == 8
        assert result.before.total_releases == 8
        assert result.before.cpu_request_total == pytest.approx(100.0 * 8)

    def test_local_chart_variants_deduplicated_by_name(self) -> None:
        """Multiple values-file variants of the same chart are deduplicated to one entry."""
        chart_main = _make_chart(name="honeybadger", replicas=1, cpu_request=100.0)
        chart_default = _make_chart(
            name="honeybadger", replicas=1, cpu_request=150.0,
            values_file="values-default.yaml",
        )
        replica_map = {("honeybadger", f"ns-{i}"): 1 for i in range(8)}
        calc = ResourceImpactCalculator()

        result = calc.compute_impact(
            [chart_main, chart_default], [], workload_replica_map=replica_map,
        )

        # Only one chart entry after deduplication (prefers values.yaml)
        assert len(result.before_charts) == 1
        assert result.before_charts[0].release_count == 8
        # Uses the main variant's cpu_request (100.0)
        assert result.before_charts[0].cpu_request_per_replica == 100.0
        assert result.before.total_replicas == 8
        assert result.before.total_releases == 8

    def test_avl005_scales_proportionally_with_cluster_replicas(self) -> None:
        """AVL005 fix should scale proportionally when cluster has more replicas.

        If the chart says replicaCount=1 but cluster has 8 replicas, and the
        fix changes replicaCount to 2 (a 2x increase), then after should be
        8 × 2 = 16.
        """
        chart = _make_cluster_chart(
            name="honeybadger", namespace="prod",
            replicas=1, cpu_request=100.0, cpu_limit=200.0,
        )
        violation = _make_violation("AVL005", "honeybadger")
        replica_map = {("honeybadger", "prod"): 8}
        calc = ResourceImpactCalculator()

        result = calc.compute_impact(
            [chart], [violation], workload_replica_map=replica_map,
        )

        # Before: 8 replicas from cluster
        assert result.before.total_replicas == 8
        # After: 8 × (2/1) = 16 (proportional scaling)
        assert result.after.total_replicas == 16
        assert result.delta.replicas_diff == 8

    def test_avl005_still_increases_when_cluster_is_single(self) -> None:
        """AVL005 should still bump 1 → 2 when cluster actually has 1 replica."""
        chart = _make_cluster_chart(
            name="my-app", namespace="prod",
            replicas=1, cpu_request=100.0, cpu_limit=200.0,
        )
        violation = _make_violation("AVL005", "my-app")
        replica_map = {("my-app", "prod"): 1}
        calc = ResourceImpactCalculator()

        result = calc.compute_impact(
            [chart], [violation], workload_replica_map=replica_map,
        )

        assert result.before.total_replicas == 1
        assert result.after.total_replicas == 2
        assert result.delta.replicas_diff == 1

    def test_avl005_scales_with_values_replicas_3(self) -> None:
        """Proportional scaling: values=1, cluster=6, fix=2 → after=12."""
        chart = _make_cluster_chart(
            name="worker", namespace="prod",
            replicas=1, cpu_request=50.0, cpu_limit=100.0,
        )
        violation = _make_violation("AVL005", "worker")
        replica_map = {("worker", "prod"): 6}
        calc = ResourceImpactCalculator()

        result = calc.compute_impact(
            [chart], [violation], workload_replica_map=replica_map,
        )

        assert result.before.total_replicas == 6
        # 6 × (2/1) = 12
        assert result.after.total_replicas == 12

    def test_cluster_matches_values_no_scaling(self) -> None:
        """When cluster replicas == values replicas, fix applies directly."""
        chart = _make_cluster_chart(
            name="api", namespace="prod",
            replicas=1, cpu_request=100.0, cpu_limit=200.0,
        )
        violation = _make_violation("AVL005", "api")
        replica_map = {("api", "prod"): 1}
        calc = ResourceImpactCalculator()

        result = calc.compute_impact(
            [chart], [violation], workload_replica_map=replica_map,
        )

        assert result.before.total_replicas == 1
        assert result.after.total_replicas == 2

    def test_local_chart_avl005_with_multiple_releases(self) -> None:
        """Local chart + AVL005 + 8 releases should scale 8 -> 16."""
        chart = _make_chart(
            name="honeybadger", replicas=1,
            cpu_request=100.0, cpu_limit=200.0,
        )
        violation = _make_violation("AVL005", "honeybadger")
        replica_map = {
            ("honeybadger", f"ns-{i}"): 1 for i in range(8)
        }
        calc = ResourceImpactCalculator()

        result = calc.compute_impact(
            [chart], [violation], workload_replica_map=replica_map,
        )

        # Before: 8 releases x 1 replica = 8
        assert result.before.total_replicas == 8
        # After: AVL005 bumps 1->2 per release, 8 releases x 2 = 16
        assert result.after.total_replicas == 16

    def test_local_chart_uneven_replicas_across_releases(self) -> None:
        """Releases with different replica counts should sum correctly.

        Real-world case: pandora has 3 replicas in default, 2 in mes-22336,
        2 in sel-32194 = 7 total (not 6 from integer division 7//3=2).
        """
        chart = _make_chart(
            name="pandora", replicas=1, cpu_request=100.0,
        )
        replica_map = {
            ("pandora", "default"): 3,
            ("pandora", "mes-22336"): 2,
            ("pandora", "sel-32194"): 2,
        }
        calc = ResourceImpactCalculator()

        result = calc.compute_impact(
            [chart], [], workload_replica_map=replica_map,
        )

        # 3 + 2 + 2 = 7 total replicas, 3 releases
        assert result.before.total_replicas == 7
        assert result.before.total_releases == 3
        assert result.before.cpu_request_total == pytest.approx(100.0 * 7)


def _make_umbrella_sub_chart(
    name: str = "redis",
    parent_chart: str = "contact-service",
    team: str = "platform",
    cpu_request: float = 100.0,
    cpu_limit: float = 500.0,
    memory_request: float = 128 * 1024**2,
    memory_limit: float = 512 * 1024**2,
    replicas: int = 1,
    values_file: str = "values.yaml",
) -> ChartInfo:
    """Create a ChartInfo representing an umbrella sub-chart."""
    return ChartInfo(
        name=name,
        team=team,
        values_file=values_file,
        parent_chart=parent_chart,
        cpu_request=cpu_request,
        cpu_limit=cpu_limit,
        memory_request=memory_request,
        memory_limit=memory_limit,
        qos_class=QoSClass.BURSTABLE,
        has_liveness=True,
        has_readiness=True,
        has_startup=False,
        has_anti_affinity=False,
        has_topology_spread=False,
        has_topology=False,
        pdb_enabled=False,
        pdb_template_exists=False,
        pdb_min_available=None,
        pdb_max_unavailable=None,
        replicas=replicas,
        priority_class=None,
    )


class TestUmbrellaSubCharts:
    """Tests for umbrella sub-charts with parent_chart field."""

    def test_same_name_different_parents_not_deduplicated(self) -> None:
        """Sub-charts with the same alias but different parents must be kept separate."""
        redis_contact = _make_umbrella_sub_chart(
            name="redis", parent_chart="contact-service",
            cpu_request=100.0, replicas=1,
        )
        redis_user = _make_umbrella_sub_chart(
            name="redis", parent_chart="user-service",
            cpu_request=200.0, replicas=2,
        )
        calc = ResourceImpactCalculator()

        result = calc.compute_impact([redis_contact, redis_user], [])

        # Both sub-charts should be present (not deduplicated)
        assert result.before.chart_count == 2
        assert len(result.before_charts) == 2
        # Total: (100 * 1) + (200 * 2) = 500
        assert result.before.cpu_request_total == pytest.approx(500.0)
        assert result.before.total_replicas == 3

    def test_same_name_same_parent_deduplicated(self) -> None:
        """Multiple values-file variants of the same sub-chart should be deduplicated."""
        redis_main = _make_umbrella_sub_chart(
            name="redis", parent_chart="contact-service",
            cpu_request=100.0, values_file="values.yaml",
        )
        redis_staging = _make_umbrella_sub_chart(
            name="redis", parent_chart="contact-service",
            cpu_request=150.0, values_file="values-staging.yaml",
        )
        calc = ResourceImpactCalculator()

        result = calc.compute_impact([redis_main, redis_staging], [])

        # Should be deduplicated to one (prefers values.yaml)
        assert result.before.chart_count == 1
        assert result.before_charts[0].cpu_request_per_replica == 100.0

    def test_violations_routed_to_correct_parent(self) -> None:
        """Violations for same-named sub-charts should be routed by parent_chart."""
        redis_contact = _make_umbrella_sub_chart(
            name="redis", parent_chart="contact-service",
            cpu_request=100.0, cpu_limit=1000.0, replicas=1,
        )
        redis_user = _make_umbrella_sub_chart(
            name="redis", parent_chart="user-service",
            cpu_request=200.0, cpu_limit=400.0, replicas=1,
        )
        # Only contact-service's redis has a violation
        violation = _make_violation(
            "RES005", "redis", parent_chart="contact-service",
        )
        calc = ResourceImpactCalculator()

        result = calc.compute_impact(
            [redis_contact, redis_user], [violation],
        )

        # contact-service redis: RES005 increases cpu request
        contact_before = result.before_charts[0]
        contact_after = result.after_charts[0]
        assert contact_after.cpu_request_per_replica > contact_before.cpu_request_per_replica

        # user-service redis: no violations, should be unchanged
        user_before = result.before_charts[1]
        user_after = result.after_charts[1]
        assert user_after.cpu_request_per_replica == user_before.cpu_request_per_replica
        assert user_after.cpu_limit_per_replica == user_before.cpu_limit_per_replica

    def test_parent_chart_propagated_to_snapshots(self) -> None:
        """ChartResourceSnapshot should carry the parent_chart value."""
        chart = _make_umbrella_sub_chart(
            name="redis", parent_chart="contact-service",
        )
        calc = ResourceImpactCalculator()

        result = calc.compute_impact([chart], [])

        assert result.before_charts[0].parent_chart == "contact-service"
        assert result.after_charts[0].parent_chart == "contact-service"

    def test_standalone_chart_has_empty_parent(self) -> None:
        """Non-umbrella charts should have empty parent_chart in snapshots."""
        chart = _make_chart(name="standalone-api")
        calc = ResourceImpactCalculator()

        result = calc.compute_impact([chart], [])

        assert result.before_charts[0].parent_chart == ""
        assert result.after_charts[0].parent_chart == ""

    def test_avl005_per_parent_sub_chart(self) -> None:
        """AVL005 for one parent's sub-chart should not affect the other parent's."""
        redis_contact = _make_umbrella_sub_chart(
            name="redis", parent_chart="contact-service",
            cpu_request=100.0, cpu_limit=200.0, replicas=1,
        )
        redis_user = _make_umbrella_sub_chart(
            name="redis", parent_chart="user-service",
            cpu_request=100.0, cpu_limit=200.0, replicas=3,
        )
        # Only contact-service redis has AVL005
        violation = _make_violation(
            "AVL005", "redis", parent_chart="contact-service",
        )
        calc = ResourceImpactCalculator()

        result = calc.compute_impact(
            [redis_contact, redis_user], [violation],
        )

        # contact-service redis: 1 -> 2 replicas
        assert result.after_charts[0].replicas == 2
        # user-service redis: unchanged at 3
        assert result.after_charts[1].replicas == 3
        # Total: 2 + 3 = 5
        assert result.after.total_replicas == 5

    def test_mixed_umbrella_and_standalone(self) -> None:
        """Fleet with both umbrella sub-charts and standalone charts."""
        redis_sub = _make_umbrella_sub_chart(
            name="redis", parent_chart="contact-service",
            cpu_request=50.0, replicas=1,
        )
        standalone_api = _make_chart(
            name="api-gateway", cpu_request=200.0, replicas=3,
        )
        calc = ResourceImpactCalculator()

        result = calc.compute_impact([redis_sub, standalone_api], [])

        assert result.before.chart_count == 2
        # (50 * 1) + (200 * 3) = 650
        assert result.before.cpu_request_total == pytest.approx(650.0)
        assert result.before.total_replicas == 4


class TestMinMaxReplicas:
    """Tests for min_replicas and max_replicas in ChartResourceSnapshot."""

    def test_single_release_min_equals_max(self) -> None:
        """Single release: min == max == total replicas."""
        chart = _make_chart(name="api", replicas=3)
        calc = ResourceImpactCalculator()

        result = calc.compute_impact([chart], [])

        snap = result.before_charts[0]
        assert snap.min_replicas == 3
        assert snap.max_replicas == 3
        assert snap.replicas == 3

    def test_cluster_chart_min_equals_max(self) -> None:
        """Cluster chart (single release): min == max."""
        chart = _make_cluster_chart(name="api", namespace="prod", replicas=1)
        replica_map = {("api", "prod"): 5}
        calc = ResourceImpactCalculator()

        result = calc.compute_impact([chart], [], workload_replica_map=replica_map)

        snap = result.before_charts[0]
        assert snap.min_replicas == 5
        assert snap.max_replicas == 5

    def test_uneven_releases_show_spread(self) -> None:
        """Multiple releases with different replica counts show min/max spread."""
        chart = _make_chart(name="pandora", replicas=1, cpu_request=100.0)
        replica_map = {
            ("pandora", "default"): 3,
            ("pandora", "mes-22336"): 2,
            ("pandora", "sel-32194"): 2,
        }
        calc = ResourceImpactCalculator()

        result = calc.compute_impact([chart], [], workload_replica_map=replica_map)

        snap = result.before_charts[0]
        assert snap.replicas == 7  # 3 + 2 + 2
        assert snap.min_replicas == 2
        assert snap.max_replicas == 3
        assert snap.release_count == 3

    def test_uniform_releases_min_equals_max(self) -> None:
        """All releases with same replica count: min == max."""
        chart = _make_chart(name="worker", replicas=1)
        replica_map = {("worker", f"ns-{i}"): 2 for i in range(5)}
        calc = ResourceImpactCalculator()

        result = calc.compute_impact([chart], [], workload_replica_map=replica_map)

        snap = result.before_charts[0]
        assert snap.replicas == 10  # 5 × 2
        assert snap.min_replicas == 2
        assert snap.max_replicas == 2

    def test_avl005_scales_min_max_proportionally(self) -> None:
        """AVL005 should scale min and max replicas proportionally."""
        chart = _make_chart(
            name="pandora", replicas=1,
            cpu_request=100.0, cpu_limit=200.0,
        )
        replica_map = {
            ("pandora", "default"): 3,
            ("pandora", "staging"): 1,
        }
        violation = _make_violation("AVL005", "pandora")
        calc = ResourceImpactCalculator()

        result = calc.compute_impact(
            [chart], [violation], workload_replica_map=replica_map,
        )

        before = result.before_charts[0]
        after = result.after_charts[0]
        # Before: total=4, min=1, max=3
        assert before.min_replicas == 1
        assert before.max_replicas == 3
        # After: ratio=2 (values 1→2), so min=2, max=6
        assert after.min_replicas == 2
        assert after.max_replicas == 6

    def test_no_replica_change_min_max_unchanged(self) -> None:
        """Resource-only violations should not change min/max replicas."""
        chart = _make_chart(
            name="api", replicas=1,
            cpu_request=100.0, cpu_limit=1000.0,
        )
        replica_map = {
            ("api", "ns-1"): 3,
            ("api", "ns-2"): 1,
        }
        violation = _make_violation("RES005", "api")
        calc = ResourceImpactCalculator()

        result = calc.compute_impact(
            [chart], [violation], workload_replica_map=replica_map,
        )

        before = result.before_charts[0]
        after = result.after_charts[0]
        # Min/max should be unchanged (RES005 only changes CPU, not replicas)
        assert after.min_replicas == before.min_replicas
        assert after.max_replicas == before.max_replicas

    def test_no_replica_map_defaults(self) -> None:
        """Without workload_replica_map, min == max == values-file replicas."""
        chart = _make_chart(name="api", replicas=2)
        calc = ResourceImpactCalculator()

        result = calc.compute_impact([chart], [])

        snap = result.before_charts[0]
        assert snap.min_replicas == 2
        assert snap.max_replicas == 2
