"""Table column configurations.

All table column definitions with widths for consistent display.
"""

from typing import NamedTuple


class ColumnWidth(NamedTuple):
    """Column definition with width."""

    label: str
    width: int


# ============================================================================
# Cluster screen tables
# ============================================================================

CLUSTER_NODES_COLUMNS: list[ColumnWidth] = [
    ColumnWidth("Name", 30),
    ColumnWidth("Status", 12),
    ColumnWidth("Type", 15),
    ColumnWidth("CPU", 10),
    ColumnWidth("Memory", 10),
    ColumnWidth("Pods", 10),
]

CLUSTER_PODS_COLUMNS: list[ColumnWidth] = [
    ColumnWidth("Namespace", 20),
    ColumnWidth("Name", 30),
    ColumnWidth("Status", 15),
    ColumnWidth("Ready", 10),
    ColumnWidth("Restarts", 10),
    ColumnWidth("Age", 15),
]

CLUSTER_EVENTS_COLUMNS: list[ColumnWidth] = [
    ColumnWidth("Time", 18),
    ColumnWidth("Type", 10),
    ColumnWidth("Reason", 15),
    ColumnWidth("Object", 30),
    ColumnWidth("Message", 50),
]

CLUSTER_PDBS_COLUMNS: list[ColumnWidth] = [
    ColumnWidth("Namespace", 20),
    ColumnWidth("Name", 25),
    ColumnWidth("Min Available", 15),
    ColumnWidth("Max Unavailable", 18),
    ColumnWidth("Status", 15),
]

CLUSTER_SINGLE_REPLICA_COLUMNS: list[ColumnWidth] = [
    ColumnWidth("Namespace", 20),
    ColumnWidth("Name", 30),
    ColumnWidth("Kind", 15),
    ColumnWidth("Status", 15),
    ColumnWidth("Node", 25),
]

CLUSTER_NODE_DIST_COLUMNS: list[ColumnWidth] = [
    ColumnWidth("Node", 25),
    ColumnWidth("CPU Request", 15),
    ColumnWidth("CPU Allocatable", 15),
    ColumnWidth("CPU %", 10),
    ColumnWidth("Mem Request", 15),
    ColumnWidth("Mem Allocatable", 15),
    ColumnWidth("Mem %", 10),
]

CLUSTER_NODE_GROUPS_COLUMNS: list[ColumnWidth] = [
    ColumnWidth("Node Group", 30),
    ColumnWidth("Nodes", 10),
    ColumnWidth("Instance Type", 20),
    ColumnWidth("CPU Capacity", 15),
    ColumnWidth("Memory Capacity", 15),
    ColumnWidth("Pods Capacity", 15),
]

CLUSTER_STATS_COLUMNS: list[ColumnWidth] = [
    ColumnWidth("Category", 30),
    ColumnWidth("Metric", 30),
    ColumnWidth("Value", 20),
]

__all__ = [
    "ColumnWidth",
    "CLUSTER_NODES_COLUMNS",
    "CLUSTER_PODS_COLUMNS",
    "CLUSTER_EVENTS_COLUMNS",
    "CLUSTER_PDBS_COLUMNS",
    "CLUSTER_SINGLE_REPLICA_COLUMNS",
    "CLUSTER_NODE_DIST_COLUMNS",
    "CLUSTER_NODE_GROUPS_COLUMNS",
    "CLUSTER_STATS_COLUMNS",
]
