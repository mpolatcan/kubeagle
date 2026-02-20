"""Event information models."""

from datetime import datetime

from pydantic import BaseModel


class EventInfo(BaseModel):
    """Basic event information."""

    type: str  # Normal, Warning
    reason: str
    message: str
    count: int
    last_timestamp: datetime
    source: str


class EventDetail(BaseModel):
    """Detailed information about a single event."""

    type: str  # Normal, Warning
    reason: str
    message: str
    count: int
    last_timestamp: str
    source: str
    involved_object: str  # namespace/name or node name
    severity: str = "INFO"
