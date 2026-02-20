"""Event parser for cluster controller - parses event data into structured formats."""

from __future__ import annotations

import math
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from typing import Any

from kubeagle.constants.enums import Severity
from kubeagle.models.events.event_info import EventDetail
from kubeagle.models.events.event_summary import EventSummary


class EventParser:
    """Parses event data into structured formats."""

    _DEFAULT_EVENT_WINDOW_HOURS = 0.25  # 15 minutes

    def __init__(self) -> None:
        """Initialize event parser."""
        pass

    @staticmethod
    def _parse_iso_timestamp(timestamp: Any) -> datetime | None:
        """Parse kubernetes timestamp strings into aware datetimes."""
        if not isinstance(timestamp, str) or not timestamp:
            return None
        with suppress(ValueError, TypeError):
            return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return None

    def _parse_event_timestamp(self, event: dict[str, Any]) -> tuple[str | None, datetime | None]:
        """Extract timestamp string and parsed datetime from event.

        Returns:
            Tuple of (timestamp_str, parsed_datetime or None)
        """
        event_time_str = (
            event.get("series", {}).get("lastObservedTime")
            or event.get("lastTimestamp")
            or event.get("deprecatedLastTimestamp")
            or event.get("eventTime")
            or event.get("metadata", {}).get("creationTimestamp")
        )
        event_datetime = self._parse_iso_timestamp(event_time_str)

        return event_time_str, event_datetime

    @staticmethod
    def _first_seen_timestamp(event: dict[str, Any]) -> datetime | None:
        """Resolve first-seen timestamp across legacy and events.k8s.io shapes."""
        first_seen_raw = (
            event.get("firstTimestamp")
            or event.get("deprecatedFirstTimestamp")
            or event.get("eventTime")
            or event.get("metadata", {}).get("creationTimestamp")
        )
        return EventParser._parse_iso_timestamp(first_seen_raw)

    @staticmethod
    def _last_seen_timestamp(event: dict[str, Any]) -> datetime | None:
        """Resolve last-seen timestamp across legacy and events.k8s.io shapes."""
        last_seen_raw = (
            event.get("series", {}).get("lastObservedTime")
            or event.get("lastTimestamp")
            or event.get("deprecatedLastTimestamp")
            or event.get("eventTime")
            or event.get("metadata", {}).get("creationTimestamp")
        )
        return EventParser._parse_iso_timestamp(last_seen_raw)

    @staticmethod
    def _parse_event_count(event: dict[str, Any]) -> int:
        """Parse event count across core/events.k8s.io shapes."""
        raw_value = (
            event.get("count")
            or event.get("deprecatedCount")
            or event.get("series", {}).get("count")
            or 1
        )
        with suppress(ValueError, TypeError):
            return max(1, int(raw_value))
        return 1

    @classmethod
    def _parse_event_count_in_window(
        cls,
        event: dict[str, Any],
        *,
        now: datetime,
        max_age_seconds: float,
        event_datetime: datetime | None = None,
    ) -> int:
        """Estimate how many repeated occurrences happened within the lookback window."""
        total_count = cls._parse_event_count(event)
        if total_count <= 1:
            return total_count

        last_seen = event_datetime or cls._last_seen_timestamp(event)
        if last_seen is None:
            return total_count

        cutoff = now - timedelta(seconds=max_age_seconds)
        if last_seen < cutoff:
            return 0

        first_seen = cls._first_seen_timestamp(event)
        if first_seen is None or last_seen <= first_seen:
            return total_count
        if first_seen >= cutoff:
            return total_count

        span_seconds = (last_seen - first_seen).total_seconds()
        if span_seconds <= 0:
            return total_count

        overlap_seconds = (last_seen - cutoff).total_seconds()
        scaled_count = math.ceil(total_count * (overlap_seconds / span_seconds))
        return max(1, min(total_count, scaled_count))

    def _is_oom_event(self, reason: str, message: str) -> bool:
        """Check if event is an OOM event."""
        return (
            reason == "OOMKilling"
            or "OOMKill" in message
            or "Out of memory" in message
        )

    def _is_node_not_ready_event(self, reason: str, involved_kind: str) -> bool:
        """Check if event indicates node not ready."""
        return involved_kind == "Node" and reason in ("NodeNotReady", "NodeNotSchedulable")

    def _is_scheduling_failure(self, reason: str) -> bool:
        """Check if event indicates scheduling failure."""
        return reason in ("FailedScheduling", "FailedCreate")

    def _is_backoff_event(self, reason: str, message: str) -> bool:
        """Check if event is a BackOff event."""
        return (
            reason == "BackOff"
            or (reason == "Failed" and "pull" in message.lower())
            or "BackOff" in message
        )

    def _is_unhealthy_event(self, reason: str) -> bool:
        """Check if event indicates probe failure."""
        return reason == "Unhealthy"

    def _is_failed_mount_event(self, reason: str) -> bool:
        """Check if event indicates volume mount failure."""
        return reason in (
            "FailedMount",
            "FailedAttachVolume",
            "FailedMapVolume",
            "VolumeResizeFailed",
            "FailedBinding",
        )

    def _is_eviction_event(self, reason: str, message: str) -> bool:
        """Check if event indicates pod eviction."""
        return (
            reason
            in (
                "Evicted",
                "Preempted",
                "Preempting",
                "EvictionThresholdMet",
                "NodePressure",
            )
            or "evict" in message.lower()
        )

    def parse_events_summary(
        self,
        events: list[dict[str, Any]],
        max_age_hours: float = _DEFAULT_EVENT_WINDOW_HOURS,
        max_recent_events: int = 20,
    ) -> EventSummary:
        """Parse events into a summary.

        Args:
            events: List of event dictionaries
            max_age_hours: Only include events newer than this
            max_recent_events: Maximum number of recent events to include

        Returns:
            EventSummary object.
        """
        now = datetime.now(timezone.utc)
        max_age_seconds = max_age_hours * 3600

        oom_count = 0
        node_not_ready_count = 0
        failed_scheduling_count = 0
        backoff_count = 0
        unhealthy_count = 0
        failed_mount_count = 0
        evicted_count = 0
        completed_count = 0
        normal_count = 0

        recent_events: list[dict[str, str]] = []
        events_with_time: list[tuple[datetime, dict[str, Any]]] = []

        for event in events:
            event_time_str, event_datetime = self._parse_event_timestamp(event)

            if event_datetime:
                age_seconds = (now - event_datetime).total_seconds()
                if age_seconds < 0 or age_seconds > max_age_seconds:
                    continue

            reason = event.get("reason", "")
            message = event.get("message", "")
            event_type = event.get("type", "Normal")
            event_count = self._parse_event_count_in_window(
                event,
                now=now,
                max_age_seconds=max_age_seconds,
                event_datetime=event_datetime,
            )
            if event_count <= 0:
                continue
            involved_object = event.get("involvedObject", {})

            is_critical = False

            if self._is_oom_event(reason, message):
                oom_count += event_count
                is_critical = True
            elif self._is_node_not_ready_event(reason, involved_object.get("kind", "")):
                node_not_ready_count += event_count
                is_critical = True
            elif self._is_scheduling_failure(reason):
                failed_scheduling_count += event_count
                is_critical = True
            elif self._is_backoff_event(reason, message):
                backoff_count += event_count
                is_critical = True
            elif self._is_unhealthy_event(reason):
                unhealthy_count += event_count
                is_critical = True
            elif self._is_failed_mount_event(reason):
                failed_mount_count += event_count
                is_critical = True
            elif self._is_eviction_event(reason, message):
                evicted_count += event_count
                is_critical = True
            elif reason == "Completed":
                completed_count += event_count
            elif event_type == "Normal":
                normal_count += event_count
            else:
                if event_type == "Warning":
                    backoff_count += event_count
                else:
                    normal_count += event_count

            if event_datetime is not None and (
                is_critical or event_type == "Warning" or event_count > 1
            ):
                obj_name = involved_object.get("name", "")
                obj_namespace = involved_object.get("namespace", "")
                obj_kind = involved_object.get("kind", "")

                if obj_kind == "Node":
                    involved = f"Node/{obj_name}"
                elif obj_namespace and obj_name:
                    involved = f"{obj_namespace}/{obj_name}"
                elif obj_name:
                    involved = obj_name
                else:
                    involved = obj_kind

                events_with_time.append(
                    (
                        event_datetime,
                        {
                            "type": event_type,
                            "reason": reason,
                            "message": message[:100] if len(message) > 100 else message,
                            "count": str(event_count),
                            "last_timestamp": event_time_str or "",
                            "involved_object": involved,
                        },
                    )
                )

        events_with_time.sort(key=lambda x: x[0], reverse=True)
        recent_events = [e[1] for e in events_with_time[:max_recent_events]]

        total_count = (
            oom_count
            + node_not_ready_count
            + failed_scheduling_count
            + backoff_count
            + unhealthy_count
            + failed_mount_count
            + evicted_count
            + completed_count
            + normal_count
        )

        return EventSummary(
            total_count=total_count,
            oom_count=oom_count,
            node_not_ready_count=node_not_ready_count,
            failed_scheduling_count=failed_scheduling_count,
            backoff_count=backoff_count,
            unhealthy_count=unhealthy_count,
            failed_mount_count=failed_mount_count,
            evicted_count=evicted_count,
            completed_count=completed_count,
            normal_count=normal_count,
            recent_events=recent_events,
            max_age_hours=max_age_hours,
            desired_healthy=0,
        )

    def parse_critical_events(
        self,
        events: list[dict[str, Any]],
        max_age_hours: float = _DEFAULT_EVENT_WINDOW_HOURS,
        limit: int = 50,
    ) -> list[EventDetail]:
        """Parse critical events.

        Args:
            events: List of event dictionaries
            max_age_hours: Only include events newer than this
            limit: Maximum number of events to return

        Returns:
            List of EventDetail objects.
        """
        now = datetime.now(timezone.utc)
        max_age_seconds = max_age_hours * 3600

        critical_events: list[EventDetail] = []

        for event in events:
            event_time_str, event_datetime = self._parse_event_timestamp(event)

            if event_datetime:
                age_seconds = (now - event_datetime).total_seconds()
                if age_seconds < 0 or age_seconds > max_age_seconds:
                    continue

            reason = event.get("reason", "")
            message = event.get("message", "")
            event_type = event.get("type", "Normal")
            event_count = self._parse_event_count_in_window(
                event,
                now=now,
                max_age_seconds=max_age_seconds,
                event_datetime=event_datetime,
            )
            if event_count <= 0:
                continue
            involved_object = event.get("involvedObject", {})
            source = event.get("source", {}).get("component", "unknown")

            is_critical = False
            severity = Severity.INFO

            if (
                self._is_oom_event(reason, message)
                or self._is_node_not_ready_event(reason, involved_object.get("kind", ""))
                or self._is_scheduling_failure(reason)
            ):
                is_critical = True
                severity = Severity.ERROR
            elif (
                self._is_backoff_event(reason, message)
                or self._is_unhealthy_event(reason)
                or self._is_failed_mount_event(reason)
            ):
                is_critical = True
                severity = Severity.WARNING
            elif self._is_eviction_event(reason, message):
                is_critical = True
                severity = Severity.ERROR

            if is_critical or event_type == "Warning":
                obj_name = involved_object.get("name", "")
                obj_namespace = involved_object.get("namespace", "")
                obj_kind = involved_object.get("kind", "")

                if obj_kind == "Node":
                    involved = obj_name
                elif obj_namespace and obj_name:
                    involved = f"{obj_namespace}/{obj_name}"
                elif obj_name:
                    involved = obj_name
                else:
                    involved = obj_kind

                critical_events.append(
                    EventDetail(
                        type=event_type,
                        reason=reason,
                        message=message,
                        count=event_count,
                        last_timestamp=event_time_str or "",
                        source=source,
                        involved_object=involved,
                        severity=severity.value if isinstance(severity, Severity) else str(severity),
                    )
                )

            if len(critical_events) >= limit:
                break

        critical_events.sort(key=lambda e: e.last_timestamp, reverse=True)
        return critical_events
