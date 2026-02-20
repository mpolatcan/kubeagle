"""Team statistics models."""

from pydantic import BaseModel


class TeamStatistics(BaseModel):
    """Statistics for a team's charts."""

    team_name: str
    chart_count: int

    # Resource totals
    cpu_request: float  # millicores
    cpu_limit: float  # millicores
    memory_request: float  # bytes
    memory_limit: float  # bytes

    # Average ratios
    avg_cpu_ratio: float
    avg_memory_ratio: float

    # Feature flags (at least one chart has it)
    has_anti_affinity: bool
    has_topology: bool
    has_probes: bool

    # Violations
    violation_count: int
