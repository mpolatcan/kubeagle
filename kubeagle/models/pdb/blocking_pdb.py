"""Blocking PDB models."""

from pydantic import BaseModel


class BlockingPDBInfo(BaseModel):
    """Information about a blocking PDB."""

    name: str
    namespace: str
    min_available: int | None = None
    max_unavailable: int | None = None
    unhealthy_policy: str
    expected_pods: int
    disruptions_allowed: int
    issues: list[str]
