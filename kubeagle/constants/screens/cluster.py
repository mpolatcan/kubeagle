"""Cluster screen constants."""

from typing import Final

# ============================================================================
# Tab IDs and Names
# ============================================================================

TAB_IDS: list[str] = [
    "tab-overview",
    "tab-nodes",
    "tab-pods",
    "tab-events",
    "tab-pdbs",
    "tab-single-replica",
    "tab-health",
    "tab-node-dist",
    "tab-groups",
    "tab-stats",
]

TAB_OVERVIEW: Final = "1: Overview"
TAB_NODES: Final = "2: Nodes"
TAB_PODS: Final = "3: Pods"
TAB_EVENTS: Final = "4: Events"
TAB_PDBS: Final = "5: PDBs"
TAB_SINGLE_REPLICA: Final = "6: Single Replica"
TAB_HEALTH: Final = "7: Health"
TAB_NODE_DIST: Final = "8: Node Dist"
TAB_GROUPS: Final = "9: Groups"
TAB_STATS: Final = "0: Stats"

# ============================================================================
# Status bar
# ============================================================================

STATUS_LABEL_CLUSTER: Final = "Cluster: "
STATUS_LABEL_NODES: Final = "Nodes: "
STATUS_LABEL_UPDATED: Final = "Last Updated: "
STATUS_NEVER: Final = "Never"
STATUS_UNKNOWN: Final = "Unknown"

# ============================================================================
# Loading messages
# ============================================================================

LOADING_INITIALIZING: Final = "Initializing..."
LOADING_CHECKING_CONNECTION: Final = "Checking cluster connection..."
LOADING_FETCHING_NODES: Final = "Fetching nodes..."
LOADING_FETCHING_EVENTS: Final = "Fetching events..."
LOADING_FETCHING_SINGLE_REPLICA: Final = "Fetching single replica workloads..."
LOADING_FETCHING_PDBS: Final = "Fetching PodDisruptionBudgets..."
LOADING_FETCHING_NODE_RESOURCES: Final = "Fetching node resources..."
LOADING_ANALYZING: Final = "Analyzing node groups..."

# ============================================================================
# Error messages
# ============================================================================

CLUSTER_ERROR_LOADING: Final = "Failed to load cluster data: {e}"

# ============================================================================
# Event window options
# ============================================================================

CLUSTER_EVENT_WINDOW_OPTIONS: Final[tuple[tuple[str, str], ...]] = (
    ("Last 15m", "0.25"),
    ("Last 30m", "0.5"),
    ("Last 1h", "1.0"),
    ("Last 2h", "2.0"),
)
CLUSTER_EVENT_WINDOW_DEFAULT: Final = "0.25"

__all__ = [
    "TAB_IDS",
    "TAB_OVERVIEW",
    "TAB_NODES",
    "TAB_PODS",
    "TAB_EVENTS",
    "TAB_PDBS",
    "TAB_SINGLE_REPLICA",
    "TAB_HEALTH",
    "TAB_NODE_DIST",
    "TAB_GROUPS",
    "TAB_STATS",
    "STATUS_LABEL_CLUSTER",
    "STATUS_LABEL_NODES",
    "STATUS_LABEL_UPDATED",
    "STATUS_NEVER",
    "STATUS_UNKNOWN",
    "LOADING_INITIALIZING",
    "LOADING_CHECKING_CONNECTION",
    "LOADING_FETCHING_NODES",
    "LOADING_FETCHING_EVENTS",
    "LOADING_FETCHING_SINGLE_REPLICA",
    "LOADING_FETCHING_PDBS",
    "LOADING_FETCHING_NODE_RESOURCES",
    "LOADING_ANALYZING",
    "CLUSTER_ERROR_LOADING",
    "CLUSTER_EVENT_WINDOW_OPTIONS",
    "CLUSTER_EVENT_WINDOW_DEFAULT",
]
