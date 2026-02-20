"""Pod distribution models."""

from pydantic import BaseModel


class PodDistributionInfo(BaseModel):
    """Pod distribution statistics across nodes."""

    total_pods: int
    min_pods_per_node: int
    max_pods_per_node: int
    avg_pods_per_node: float
    p95_pods_per_node: float

    # Nodes with highest pod counts
    high_pod_nodes: list[
        dict[str, object]
    ]  # name, node_group, pod_count, cpu_pct, mem_pct

    # Distribution by node group
    by_node_group: dict[str, dict[str, object]]
