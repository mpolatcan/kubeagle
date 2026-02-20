"""Event summary models."""

from pydantic import BaseModel


class EventSummary(BaseModel):
    """Comprehensive event analysis summary for the cluster."""

    total_count: int
    oom_count: int
    node_not_ready_count: int
    failed_scheduling_count: int
    backoff_count: int
    unhealthy_count: int
    failed_mount_count: int
    evicted_count: int
    completed_count: int
    normal_count: int
    recent_events: list[dict[str, str]]  # Last N events with full details
    max_age_hours: float = 1.0
    desired_healthy: int = 0
