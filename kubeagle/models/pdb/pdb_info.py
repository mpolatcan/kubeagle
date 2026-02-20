"""PDB information models."""

from pydantic import BaseModel


class PDBInfo(BaseModel):
    """Pod Disruption Budget information."""

    name: str
    namespace: str
    kind: str  # Deployment, StatefulSet, etc.
    min_available: int | None
    max_unavailable: int | None
    min_unavailable: int | None
    max_available: int | None
    current_healthy: int
    desired_healthy: int
    expected_pods: int
    disruptions_allowed: int
    unhealthy_pod_eviction_policy: str
    selector_match_labels: dict[str, str] | None = None
    # Blocking analysis fields
    is_blocking: bool = False
    blocking_reason: str | None = None
    conflict_type: str | None = None
