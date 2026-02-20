"""Event analysis utilities for EKS cluster data operations."""

from __future__ import annotations

import json
import logging
from contextlib import suppress
from datetime import datetime, timezone
from typing import Any

from kubeagle.constants.enums import Severity

logger = logging.getLogger(__name__)


class EventAnalyzer:
    """Analyzes Kubernetes cluster events for various issue categories."""

    _OOM_REASONS = frozenset(["OOMKilling"])
    _BACKOFF_REASONS = frozenset(["BackOff", "Failed"])
    _UNHEALTHY_REASONS = frozenset(["Unhealthy"])
    _FAILED_MOUNT_REASONS = frozenset([
        "FailedMount",
        "FailedAttachVolume",
        "FailedMapVolume",
        "VolumeResizeFailed",
        "FailedBinding",
    ])
    _EVICTION_REASONS = frozenset([
        "Evicted",
        "Preempted",
        "Preempting",
        "EvictionThresholdMet",
        "NodePressure",
    ])
    _NODE_NOT_READY_REASONS = frozenset(["NodeNotReady", "NodeNotSchedulable"])
    _SCHEDULING_REASONS = frozenset(["FailedScheduling", "FailedCreate"])

    @classmethod
    def is_oom_event(cls, reason: str, message: str) -> bool:
        """Check if event is an OOM (Out of Memory) event."""
        return (
            reason in cls._OOM_REASONS
            or "OOMKill" in message
            or "Out of memory" in message
        )

    @classmethod
    def is_node_not_ready_event(cls, reason: str, involved_object_kind: str) -> bool:
        """Check if event indicates node not ready."""
        return (
            involved_object_kind == "Node"
            and reason in cls._NODE_NOT_READY_REASONS
        )

    @classmethod
    def is_scheduling_failure(cls, reason: str) -> bool:
        """Check if event indicates scheduling failure."""
        return reason in cls._SCHEDULING_REASONS

    @classmethod
    def is_backoff_event(cls, reason: str, message: str) -> bool:
        """Check if event is a BackOff event."""
        return (
            reason in cls._BACKOFF_REASONS
            and (
                reason == "BackOff"
                or (reason == "Failed" and "pull" in message.lower())
                or "BackOff" in message
            )
        )

    @classmethod
    def is_unhealthy_event(cls, reason: str) -> bool:
        """Check if event indicates probe failure."""
        return reason in cls._UNHEALTHY_REASONS

    @classmethod
    def is_failed_mount_event(cls, reason: str) -> bool:
        """Check if event indicates volume mount failure."""
        return reason in cls._FAILED_MOUNT_REASONS

    @classmethod
    def is_eviction_event(cls, reason: str, message: str) -> bool:
        """Check if event indicates pod eviction."""
        return (
            reason in cls._EVICTION_REASONS
            or "evict" in message.lower()
        )

    @classmethod
    def parse_event_timestamp(
        cls, event: dict[str, Any]
    ) -> tuple[str | None, datetime | None]:
        """Extract timestamp string and parsed datetime from event."""
        event_time_str = (
            event.get("lastTimestamp")
            or event.get("eventTime")
            or event.get("metadata", {}).get("creationTimestamp")
        )
        event_datetime: datetime | None = None

        if event_time_str:
            with suppress(ValueError, TypeError):
                event_datetime = datetime.fromisoformat(
                    event_time_str.replace("Z", "+00:00")
                )

        return event_time_str, event_datetime

    @classmethod
    def is_event_recent(
        cls,
        event_datetime: datetime | None,
        max_age_seconds: float,
    ) -> bool:
        """Check if event is within the age threshold."""
        if event_datetime is None:
            return True

        now = datetime.now(timezone.utc)
        age_seconds = (now - event_datetime).total_seconds()
        return 0 <= age_seconds <= max_age_seconds

    @classmethod
    def format_involved_object(cls, event: dict[str, Any]) -> str:
        """Format the involved object for display."""
        involved_object = event.get("involvedObject", {})
        obj_name = involved_object.get("name", "")
        obj_namespace = involved_object.get("namespace", "")
        obj_kind = involved_object.get("kind", "")

        if obj_kind == "Node":
            return f"Node/{obj_name}"
        elif obj_namespace and obj_name:
            return f"{obj_namespace}/{obj_name}"
        elif obj_name:
            return obj_name
        else:
            return obj_kind

    @classmethod
    def classify_event(
        cls,
        event: dict[str, Any],
        max_age_seconds: float,
    ) -> dict[str, Any] | None:
        """Classify a single event and return its details."""
        event_time_str, event_datetime = cls.parse_event_timestamp(event)

        if not cls.is_event_recent(event_datetime, max_age_seconds):
            return None

        reason = event.get("reason", "")
        message = event.get("message", "")
        event_type = event.get("type", "Normal")
        event_count = event.get("count", 1)
        involved_object = event.get("involvedObject", {})

        is_critical = False
        severity = Severity.INFO

        if (
            cls.is_oom_event(reason, message)
            or cls.is_node_not_ready_event(reason, involved_object.get("kind", ""))
            or cls.is_scheduling_failure(reason)
        ):
            is_critical = True
            severity = Severity.ERROR
        elif (
            cls.is_backoff_event(reason, message)
            or cls.is_unhealthy_event(reason)
            or cls.is_failed_mount_event(reason)
        ):
            is_critical = True
            severity = Severity.WARNING
        elif cls.is_eviction_event(reason, message):
            is_critical = True
            severity = Severity.ERROR

        return {
            "type": event_type,
            "reason": reason,
            "message": message,
            "count": event_count,
            "last_timestamp": event_time_str or "",
            "involved_object": cls.format_involved_object(event),
            "is_critical": is_critical,
            "severity": severity,
        }

    @classmethod
    def parse_events_json(cls, output: str) -> dict[str, Any]:
        """Parse events JSON output safely."""
        if not output:
            return {"events": [], "error": None}

        try:
            data = json.loads(output)
            return {"events": data.get("items", []), "error": None}
        except json.JSONDecodeError:
            logger.exception("Error parsing events JSON")
            return {"events": [], "error": "Error parsing events JSON"}


def count_events_by_category(
    events: list[dict[str, Any]],
    max_age_hours: float = 1.0,
) -> dict[str, int]:
    """Count events by category (OOM, node_not_ready, etc.)."""
    analyzer = EventAnalyzer()
    max_age_seconds = max_age_hours * 3600

    counts: dict[str, int] = {
        "oom": 0,
        "node_not_ready": 0,
        "failed_scheduling": 0,
        "backoff": 0,
        "unhealthy": 0,
        "failed_mount": 0,
        "evicted": 0,
    }

    for event in events:
        event_time_str = (
            event.get("lastTimestamp")
            or event.get("eventTime")
            or event.get("metadata", {}).get("creationTimestamp")
        )

        if event_time_str:
            try:
                event_time = datetime.fromisoformat(
                    event_time_str.replace("Z", "+00:00")
                )
                age_seconds = (datetime.now(timezone.utc) - event_time).total_seconds()
                if age_seconds < 0 or age_seconds > max_age_seconds:
                    continue
            except (ValueError, TypeError):
                pass

        reason = event.get("reason", "")
        message = event.get("message", "")
        event_count = event.get("count", 1)

        if analyzer.is_oom_event(reason, message):
            counts["oom"] += event_count
        elif analyzer.is_node_not_ready_event(
            reason, event.get("involvedObject", {}).get("kind", "")
        ):
            counts["node_not_ready"] += event_count
        elif analyzer.is_scheduling_failure(reason):
            counts["failed_scheduling"] += event_count
        elif analyzer.is_backoff_event(reason, message):
            counts["backoff"] += event_count
        elif analyzer.is_unhealthy_event(reason):
            counts["unhealthy"] += event_count
        elif analyzer.is_failed_mount_event(reason):
            counts["failed_mount"] += event_count
        elif analyzer.is_eviction_event(reason, message):
            counts["evicted"] += event_count

    return counts


__all__ = ["EventAnalyzer", "count_events_by_category"]
