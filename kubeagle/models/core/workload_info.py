"""Workload information models."""

from pydantic import BaseModel


class SingleReplicaWorkloadInfo(BaseModel):
    """Extended single replica workload information with Helm release association."""

    name: str
    namespace: str
    kind: str  # Deployment or StatefulSet
    replicas: int
    ready_replicas: int
    helm_release: str | None = None
    chart_name: str | None = None
    status: str = "Unknown"
    is_system_workload: bool = False
    node_name: str | None = None
