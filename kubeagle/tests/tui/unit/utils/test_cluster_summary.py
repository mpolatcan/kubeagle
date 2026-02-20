"""Unit tests for shared cluster summary helpers."""

from __future__ import annotations

from types import SimpleNamespace

from kubeagle.constants.enums import NodeStatus
from kubeagle.utils.cluster_summary import (
    count_blocking_pdbs,
    count_node_groups,
    summarize_nodes,
)


def test_count_node_groups_supports_wrapped_and_direct_payloads() -> None:
    """Node-group counts should support both payload layouts."""
    assert count_node_groups({"group-a": {}, "group-b": {}}) == 2
    assert count_node_groups({"node_groups": {"group-a": {}, "group-b": {}}}) == 2


def test_summarize_nodes_handles_enum_and_string_status() -> None:
    """Ready counts should work with enum-backed and string-backed node status."""
    nodes = [
        SimpleNamespace(
            status=NodeStatus.READY,
            taints=[],
            availability_zone="us-east-1a",
            instance_type="m5.large",
        ),
        SimpleNamespace(
            status="NotReady",
            taints=[{"key": "node.kubernetes.io/unschedulable"}],
            availability_zone="us-east-1b",
            instance_type="m5.xlarge",
        ),
    ]

    summary = summarize_nodes(nodes)

    assert summary["node_count"] == 2
    assert summary["ready_count"] == 1
    assert summary["not_ready_count"] == 1
    assert summary["cordoned_count"] == 1
    assert summary["az_count"] == 2
    assert summary["instance_type_count"] == 2


def test_count_blocking_pdbs_supports_objects_and_mappings() -> None:
    """Blocking PDB count should support model objects and mapping fallbacks."""
    pdbs = [
        SimpleNamespace(is_blocking=True),
        SimpleNamespace(is_blocking=False),
        {"disruptions_allowed": 0},
        {"disruptions_allowed": 1},
    ]

    assert count_blocking_pdbs(pdbs) == 2

