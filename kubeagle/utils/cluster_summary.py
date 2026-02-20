"""Shared cluster-summary helpers used by Home and Cluster screens."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def count_node_groups(allocated_data: Mapping[str, Any] | None) -> int:
    """Count node groups from allocated-analysis payload."""
    if not allocated_data:
        return 0
    node_groups = allocated_data.get("node_groups")
    if isinstance(node_groups, Mapping):
        return len(node_groups)
    return len(allocated_data)


def summarize_nodes(nodes: Sequence[Any]) -> dict[str, int]:
    """Build shared node summary counters from node payloads."""
    node_count = len(nodes)
    ready_count = sum(1 for node in nodes if _is_ready_node(node))
    not_ready_count = node_count - ready_count
    cordoned_count = sum(1 for node in nodes if _is_cordoned_node(node))
    az_count = len(
        {
            getattr(node, "availability_zone", None)
            for node in nodes
            if getattr(node, "availability_zone", None)
        }
    )
    instance_type_count = len(
        {
            getattr(node, "instance_type", None)
            for node in nodes
            if getattr(node, "instance_type", None)
        }
    )
    return {
        "node_count": node_count,
        "ready_count": ready_count,
        "not_ready_count": not_ready_count,
        "cordoned_count": cordoned_count,
        "az_count": az_count,
        "instance_type_count": instance_type_count,
    }


def count_blocking_pdbs(pdbs: Sequence[Any]) -> int:
    """Count blocking PDBs from model or mapping payloads."""
    blocking_count = 0
    for pdb in pdbs:
        if hasattr(pdb, "is_blocking"):
            if bool(pdb.is_blocking):
                blocking_count += 1
            continue

        disruptions_allowed: Any = None
        if hasattr(pdb, "disruptions_allowed"):
            disruptions_allowed = pdb.disruptions_allowed
        elif isinstance(pdb, Mapping):
            disruptions_allowed = pdb.get("disruptions_allowed")

        try:
            if disruptions_allowed is not None and int(disruptions_allowed) <= 0:
                blocking_count += 1
        except (TypeError, ValueError):
            continue
    return blocking_count


def _is_ready_node(node: Any) -> bool:
    """Return True when a node's status resolves to Ready."""
    status = getattr(node, "status", None)
    status_value = getattr(status, "value", status)
    return str(status_value).lower() == "ready"


def _is_cordoned_node(node: Any) -> bool:
    """Return True when a node includes unschedulable taint."""
    taints = getattr(node, "taints", None)
    if not isinstance(taints, Sequence):
        return False
    for taint in taints:
        key = taint.get("key") if isinstance(taint, Mapping) else getattr(taint, "key", None)
        if key == "node.kubernetes.io/unschedulable":
            return True
    return False
