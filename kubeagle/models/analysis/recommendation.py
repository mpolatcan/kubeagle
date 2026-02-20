"""Recommendation models."""

from pydantic import BaseModel

from kubeagle.constants.enums import Severity


class Recommendation(BaseModel):
    """Actionable recommendation from analysis."""

    id: str
    category: str  # "eks", "helm", "security", "reliability"
    severity: Severity
    title: str
    description: str
    affected_resources: list[str]  # Chart names, PDB names, etc.
    recommended_action: str
    yaml_example: str | None = None


class ExtremeLimitRatio(BaseModel):
    """Chart with extreme limit/request ratio."""

    chart_name: str
    team: str

    # CPU
    cpu_request: float  # millicores
    cpu_limit: float  # millicores
    cpu_ratio: float

    # Memory
    memory_request: float  # bytes
    memory_limit: float  # bytes
    memory_ratio: float

    # The maximum ratio (CPU or memory)
    max_ratio: float
