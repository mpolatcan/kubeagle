"""Chart information models."""

from pydantic import BaseModel

from kubeagle.constants.enums import QoSClass


class ChartInfo(BaseModel):
    """Helm chart configuration information."""

    name: str
    team: str
    values_file: str
    namespace: str | None = None
    cpu_request: float
    cpu_limit: float
    memory_request: float
    memory_limit: float
    qos_class: QoSClass
    has_liveness: bool
    has_readiness: bool
    has_startup: bool
    has_anti_affinity: bool
    has_topology_spread: bool
    has_topology: bool  # Alias for has_topology_spread for CLI compatibility
    pdb_enabled: bool
    pdb_template_exists: bool
    pdb_min_available: int | None
    pdb_max_unavailable: int | None
    replicas: int | None
    priority_class: str | None
    deployed_values_content: str | None = None


class HelmReleaseInfo(BaseModel):
    """Represents a Helm release from the cluster."""

    name: str
    namespace: str
    chart: str
    version: str
    app_version: str
    status: str
