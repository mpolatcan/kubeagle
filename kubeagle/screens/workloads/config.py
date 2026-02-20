"""Workloads screen configuration constants."""

from __future__ import annotations

TAB_WORKLOADS_ALL = "tab-workloads-all"
TAB_WORKLOADS_EXTREME_RATIOS = "tab-workloads-extreme-ratios"
TAB_WORKLOADS_SINGLE_REPLICA = "tab-workloads-single-replica"
TAB_WORKLOADS_MISSING_PDB = "tab-workloads-missing-pdb"
TAB_WORKLOADS_NODE_ANALYSIS = "tab-workloads-node-analysis"

WORKLOAD_VIEW_ALL = "all"
WORKLOAD_VIEW_EXTREME_RATIOS = "extreme_ratios"
WORKLOAD_VIEW_SINGLE_REPLICA = "single_replica"
WORKLOAD_VIEW_MISSING_PDB = "missing_pdb"
WORKLOAD_VIEW_NODE_ANALYSIS = "node_analysis"

WORKLOADS_TAB_IDS: list[str] = [
    TAB_WORKLOADS_ALL,
    TAB_WORKLOADS_EXTREME_RATIOS,
    TAB_WORKLOADS_SINGLE_REPLICA,
    TAB_WORKLOADS_MISSING_PDB,
    TAB_WORKLOADS_NODE_ANALYSIS,
]

WORKLOADS_TAB_LABELS: dict[str, str] = {
    TAB_WORKLOADS_ALL: "All",
    TAB_WORKLOADS_EXTREME_RATIOS: "Extreme Ratios",
    TAB_WORKLOADS_SINGLE_REPLICA: "Single Replica",
    TAB_WORKLOADS_MISSING_PDB: "Missing PDB",
    TAB_WORKLOADS_NODE_ANALYSIS: "Resource Usage",
}

WORKLOAD_VIEW_FILTER_BY_TAB: dict[str, str] = {
    TAB_WORKLOADS_ALL: WORKLOAD_VIEW_ALL,
    TAB_WORKLOADS_EXTREME_RATIOS: WORKLOAD_VIEW_EXTREME_RATIOS,
    TAB_WORKLOADS_SINGLE_REPLICA: WORKLOAD_VIEW_SINGLE_REPLICA,
    TAB_WORKLOADS_MISSING_PDB: WORKLOAD_VIEW_MISSING_PDB,
    TAB_WORKLOADS_NODE_ANALYSIS: WORKLOAD_VIEW_NODE_ANALYSIS,
}

WORKLOADS_TABLE_ID_BY_TAB: dict[str, str] = {
    TAB_WORKLOADS_ALL: "workloads-all-table",
    TAB_WORKLOADS_EXTREME_RATIOS: "workloads-extreme-ratios-table",
    TAB_WORKLOADS_SINGLE_REPLICA: "workloads-single-replica-table",
    TAB_WORKLOADS_MISSING_PDB: "workloads-missing-pdb-table",
    TAB_WORKLOADS_NODE_ANALYSIS: "workloads-node-analysis-table",
}

WORKLOADS_RESOURCE_BASE_COLUMNS: list[tuple[str, int]] = [
    ("Namespace", 20),
    ("Kind", 12),
    ("Name", 76),
    ("Restarts", 42),
    ("CPU R/L", 21),
    ("Mem R/L", 23),
    ("PDB", 10),
]

WORKLOADS_RESOURCE_NODE_ANALYSIS_BASE_COLUMNS: list[tuple[str, int]] = [
    ("Namespace", 20),
    ("Kind", 12),
    ("Name", 76),
    ("CPU R/L", 21),
    ("Mem R/L", 23),
    ("Restarts", 42),
]

WORKLOADS_RESOURCE_NODE_ANALYSIS_COLUMNS: list[tuple[str, int]] = [
    *WORKLOADS_RESOURCE_NODE_ANALYSIS_BASE_COLUMNS,
    ("Nodes", 8),
    ("Node CPU Usage/Req/Lim Avg", 34),
    ("Node CPU Usage/Req/Lim Max", 34),
    ("Node CPU Usage/Req/Lim P95", 34),
    ("Node Mem Usage/Req/Lim Avg", 34),
    ("Node Mem Usage/Req/Lim Max", 34),
    ("Node Mem Usage/Req/Lim P95", 34),
    ("Workload CPU Usage Avg/Max/P95", 32),
    ("Workload Mem Usage Avg/Max/P95", 32),
]

WORKLOADS_RESOURCE_BASE_HEADER_TOOLTIPS: dict[str, str] = {
    "Namespace": "Namespace that owns this workload.",
    "Kind": "Kubernetes workload kind.",
    "Name": "Kubernetes workload name colorized by runtime status, prefixed with a health-colored ⎈ when Helm-managed, including desired/ready replicas.",
    "Restarts": "Total container restart count across pods currently assigned to this workload, with aggregated restart reason counts in parentheses.",
    "CPU R/L": "Total CPU request/limit across workload containers, including inline CPU ratio.",
    "Mem R/L": "Total memory request/limit across workload containers, including inline memory ratio.",
    "PDB": "Whether a PodDisruptionBudget selector matches this workload.",
}

WORKLOADS_RESOURCE_NODE_ANALYSIS_HEADER_TOOLTIPS: dict[str, str] = {
    **WORKLOADS_RESOURCE_BASE_HEADER_TOOLTIPS,
    "Nodes": "Assigned node count for running workload pods.",
    "Node CPU Usage/Req/Lim Avg": "Node CPU Avg values in Usage/Request/Limit order (usage from kubectl top node, request/limit as allocatable percentages).",
    "Node CPU Usage/Req/Lim Max": "Node CPU Max values in Usage/Request/Limit order (usage from kubectl top node, request/limit as allocatable percentages).",
    "Node CPU Usage/Req/Lim P95": "Node CPU P95 values in Usage/Request/Limit order (usage from kubectl top node, request/limit as allocatable percentages).",
    "Node Mem Usage/Req/Lim Avg": "Node memory Avg values in Usage/Request/Limit order (usage from kubectl top node, request/limit as allocatable percentages).",
    "Node Mem Usage/Req/Lim Max": "Node memory Max values in Usage/Request/Limit order (usage from kubectl top node, request/limit as allocatable percentages).",
    "Node Mem Usage/Req/Lim P95": "Node memory P95 values in Usage/Request/Limit order (usage from kubectl top node, request/limit as allocatable percentages).",
    "Workload CPU Usage Avg/Max/P95": "Workload CPU usage from kubectl top pod (aggregated from workload pods), shown as raw usage with % of assigned-node allocatable in parentheses (Avg/Max/P95).",
    "Workload Mem Usage Avg/Max/P95": "Workload memory usage from kubectl top pod (aggregated from workload pods), shown as raw usage with % of assigned-node allocatable in parentheses (Avg/Max/P95).",
}

WORKLOADS_TABLE_COLUMNS_BY_TAB: dict[str, list[tuple[str, int]]] = {
    TAB_WORKLOADS_ALL: WORKLOADS_RESOURCE_BASE_COLUMNS,
    TAB_WORKLOADS_EXTREME_RATIOS: WORKLOADS_RESOURCE_BASE_COLUMNS,
    TAB_WORKLOADS_SINGLE_REPLICA: WORKLOADS_RESOURCE_BASE_COLUMNS,
    TAB_WORKLOADS_MISSING_PDB: WORKLOADS_RESOURCE_BASE_COLUMNS,
    TAB_WORKLOADS_NODE_ANALYSIS: WORKLOADS_RESOURCE_NODE_ANALYSIS_COLUMNS,
}

WORKLOADS_HEADER_TOOLTIPS_BY_TAB: dict[str, dict[str, str]] = {
    TAB_WORKLOADS_ALL: WORKLOADS_RESOURCE_BASE_HEADER_TOOLTIPS,
    TAB_WORKLOADS_EXTREME_RATIOS: WORKLOADS_RESOURCE_BASE_HEADER_TOOLTIPS,
    TAB_WORKLOADS_SINGLE_REPLICA: WORKLOADS_RESOURCE_BASE_HEADER_TOOLTIPS,
    TAB_WORKLOADS_MISSING_PDB: WORKLOADS_RESOURCE_BASE_HEADER_TOOLTIPS,
    TAB_WORKLOADS_NODE_ANALYSIS: WORKLOADS_RESOURCE_NODE_ANALYSIS_HEADER_TOOLTIPS,
}

SORT_BY_NAME = "name"
SORT_BY_NAMESPACE = "namespace"
SORT_BY_KIND = "kind"
SORT_BY_CPU_REQUEST = "cpu_request"
SORT_BY_CPU_LIMIT = "cpu_limit"
SORT_BY_CPU_RATIO = "cpu_ratio"
SORT_BY_MEMORY_REQUEST = "memory_request"
SORT_BY_MEMORY_LIMIT = "memory_limit"
SORT_BY_MEMORY_RATIO = "memory_ratio"
SORT_BY_RESTARTS = "restarts"
SORT_BY_STATUS = "status"
SORT_BY_NODE_CPU_USAGE_AVG = "node_cpu_usage_avg"
SORT_BY_NODE_CPU_REQ_AVG = "node_cpu_req_avg"
SORT_BY_NODE_CPU_LIM_AVG = "node_cpu_lim_avg"
SORT_BY_NODE_CPU_USAGE_MAX = "node_cpu_usage_max"
SORT_BY_NODE_CPU_REQ_MAX = "node_cpu_req_max"
SORT_BY_NODE_CPU_LIM_MAX = "node_cpu_lim_max"
SORT_BY_NODE_CPU_USAGE_P95 = "node_cpu_usage_p95"
SORT_BY_NODE_CPU_REQ_P95 = "node_cpu_req_p95"
SORT_BY_NODE_CPU_LIM_P95 = "node_cpu_lim_p95"
SORT_BY_NODE_MEM_USAGE_AVG = "node_mem_usage_avg"
SORT_BY_NODE_MEM_REQ_AVG = "node_mem_req_avg"
SORT_BY_NODE_MEM_LIM_AVG = "node_mem_lim_avg"
SORT_BY_NODE_MEM_USAGE_MAX = "node_mem_usage_max"
SORT_BY_NODE_MEM_REQ_MAX = "node_mem_req_max"
SORT_BY_NODE_MEM_LIM_MAX = "node_mem_lim_max"
SORT_BY_NODE_MEM_USAGE_P95 = "node_mem_usage_p95"
SORT_BY_NODE_MEM_REQ_P95 = "node_mem_req_p95"
SORT_BY_NODE_MEM_LIM_P95 = "node_mem_lim_p95"
SORT_BY_WORKLOAD_CPU_USAGE_AVG = "workload_cpu_usage_avg"
SORT_BY_WORKLOAD_CPU_USAGE_MAX = "workload_cpu_usage_max"
SORT_BY_WORKLOAD_CPU_USAGE_P95 = "workload_cpu_usage_p95"
SORT_BY_WORKLOAD_MEM_USAGE_AVG = "workload_mem_usage_avg"
SORT_BY_WORKLOAD_MEM_USAGE_MAX = "workload_mem_usage_max"
SORT_BY_WORKLOAD_MEM_USAGE_P95 = "workload_mem_usage_p95"

WORKLOADS_SORT_OPTIONS: list[tuple[str, str]] = [
    ("Name", SORT_BY_NAME),
    ("Namespace", SORT_BY_NAMESPACE),
    ("Kind", SORT_BY_KIND),
    ("CPU Request", SORT_BY_CPU_REQUEST),
    ("CPU Limit", SORT_BY_CPU_LIMIT),
    ("CPU Ratio", SORT_BY_CPU_RATIO),
    ("Memory Request", SORT_BY_MEMORY_REQUEST),
    ("Memory Limit", SORT_BY_MEMORY_LIMIT),
    ("Memory Ratio", SORT_BY_MEMORY_RATIO),
    ("Restarts", SORT_BY_RESTARTS),
    ("Status", SORT_BY_STATUS),
    ("Node CPU Usage Avg", SORT_BY_NODE_CPU_USAGE_AVG),
    ("Node CPU Req Avg", SORT_BY_NODE_CPU_REQ_AVG),
    ("Node CPU Lim Avg", SORT_BY_NODE_CPU_LIM_AVG),
    ("Node CPU Usage Max", SORT_BY_NODE_CPU_USAGE_MAX),
    ("Node CPU Req Max", SORT_BY_NODE_CPU_REQ_MAX),
    ("Node CPU Lim Max", SORT_BY_NODE_CPU_LIM_MAX),
    ("Node CPU Usage P95", SORT_BY_NODE_CPU_USAGE_P95),
    ("Node CPU Req P95", SORT_BY_NODE_CPU_REQ_P95),
    ("Node CPU Lim P95", SORT_BY_NODE_CPU_LIM_P95),
    ("Node Mem Usage Avg", SORT_BY_NODE_MEM_USAGE_AVG),
    ("Node Mem Req Avg", SORT_BY_NODE_MEM_REQ_AVG),
    ("Node Mem Lim Avg", SORT_BY_NODE_MEM_LIM_AVG),
    ("Node Mem Usage Max", SORT_BY_NODE_MEM_USAGE_MAX),
    ("Node Mem Req Max", SORT_BY_NODE_MEM_REQ_MAX),
    ("Node Mem Lim Max", SORT_BY_NODE_MEM_LIM_MAX),
    ("Node Mem Usage P95", SORT_BY_NODE_MEM_USAGE_P95),
    ("Node Mem Req P95", SORT_BY_NODE_MEM_REQ_P95),
    ("Node Mem Lim P95", SORT_BY_NODE_MEM_LIM_P95),
    ("Workload CPU Usage Avg", SORT_BY_WORKLOAD_CPU_USAGE_AVG),
    ("Workload CPU Usage Max", SORT_BY_WORKLOAD_CPU_USAGE_MAX),
    ("Workload CPU Usage P95", SORT_BY_WORKLOAD_CPU_USAGE_P95),
    ("Workload Mem Usage Avg", SORT_BY_WORKLOAD_MEM_USAGE_AVG),
    ("Workload Mem Usage Max", SORT_BY_WORKLOAD_MEM_USAGE_MAX),
    ("Workload Mem Usage P95", SORT_BY_WORKLOAD_MEM_USAGE_P95),
]
