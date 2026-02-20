"""Node information models."""

from pydantic import BaseModel

from kubeagle.constants.enums import NodeStatus


class NodeInfo(BaseModel):
    """Basic node information."""

    name: str
    status: NodeStatus
    node_group: str
    instance_type: str
    availability_zone: str
    cpu_allocatable: float
    memory_allocatable: float  # In bytes
    cpu_requests: float
    memory_requests: float  # In bytes
    cpu_limits: float
    memory_limits: float  # In bytes
    pod_count: int
    pod_capacity: int
    # Extended fields for controller methods
    kubelet_version: str = ""
    conditions: dict[str, str] = {}
    taints: list[dict[str, str]] = []


class NodeResourceInfo(BaseModel):
    """Detailed node resource information with allocation percentages."""

    name: str
    status: NodeStatus
    node_group: str
    instance_type: str
    availability_zone: str
    kubelet_version: str

    # Allocatable resources
    cpu_allocatable: float  # In millicores
    memory_allocatable: float  # In bytes
    max_pods: int

    # Current requests/limits (from running pods)
    cpu_requests: float  # In millicores
    cpu_limits: float  # In millicores
    memory_requests: float  # In bytes
    memory_limits: float  # In bytes

    # Pod count
    pod_count: int

    # Allocation percentages
    cpu_req_pct: float
    cpu_lim_pct: float
    mem_req_pct: float
    mem_lim_pct: float
    pod_pct: float

    # Health status
    is_ready: bool
    is_healthy: bool
    is_cordoned: bool

    # Node conditions and taints
    conditions: dict[str, str]  # condition_type -> status
    taints: list[dict[str, str]]  # List of taints with key, effect, value
