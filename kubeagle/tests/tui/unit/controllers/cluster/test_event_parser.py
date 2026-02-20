"""Tests for event parser."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from kubeagle.controllers.cluster.parsers.event_parser import EventParser


class TestEventParser:
    """Tests for EventParser class."""

    @pytest.fixture
    def parser(self) -> EventParser:
        """Create EventParser instance."""
        return EventParser()

    def test_parser_init(self, parser: EventParser) -> None:
        """Test EventParser initialization."""
        assert isinstance(parser, EventParser)

    def test_parse_event_timestamp_with_last_timestamp(self, parser: EventParser) -> None:
        """Test _parse_event_timestamp extracts lastTimestamp."""
        event = {"lastTimestamp": "2024-01-15T10:30:00Z"}
        timestamp, dt = parser._parse_event_timestamp(event)

        assert timestamp == "2024-01-15T10:30:00Z"
        assert dt is not None
        assert dt.year == 2024

    def test_parse_event_timestamp_with_event_time(self, parser: EventParser) -> None:
        """Test _parse_event_timestamp falls back to eventTime."""
        event = {"eventTime": "2024-01-15T10:30:00Z"}
        timestamp, dt = parser._parse_event_timestamp(event)

        assert timestamp == "2024-01-15T10:30:00Z"
        assert dt is not None

    def test_parse_event_timestamp_with_series_last_observed_time(
        self,
        parser: EventParser,
    ) -> None:
        """Test _parse_event_timestamp supports events.k8s.io series timestamp."""
        event = {"series": {"lastObservedTime": "2024-01-15T10:30:00Z"}}
        timestamp, dt = parser._parse_event_timestamp(event)

        assert timestamp == "2024-01-15T10:30:00Z"
        assert dt is not None

    def test_parse_event_timestamp_prefers_series_last_observed_time(
        self,
        parser: EventParser,
    ) -> None:
        """Series timestamp should take priority over stale legacy lastTimestamp."""
        event = {
            "lastTimestamp": "2024-01-15T09:30:00Z",
            "series": {"lastObservedTime": "2024-01-15T10:30:00Z"},
        }
        timestamp, dt = parser._parse_event_timestamp(event)

        assert timestamp == "2024-01-15T10:30:00Z"
        assert dt is not None

    def test_parse_event_timestamp_no_timestamp(self, parser: EventParser) -> None:
        """Test _parse_event_timestamp handles missing timestamp."""
        event = {"reason": "Test"}
        timestamp, dt = parser._parse_event_timestamp(event)

        assert timestamp is None
        assert dt is None

    def test_is_oom_event_true(self, parser: EventParser) -> None:
        """Test _is_oom_event identifies OOM events."""
        assert parser._is_oom_event("OOMKilling", "container out of memory") is True
        assert parser._is_oom_event("Reason", "OOMKill detected") is True
        assert parser._is_oom_event("Reason", "Out of memory error") is True

    def test_is_oom_event_false(self, parser: EventParser) -> None:
        """Test _is_oom_event rejects non-OOM events."""
        assert parser._is_oom_event("Scheduled", "pod scheduled") is False
        assert parser._is_oom_event("Reason", "normal message") is False

    def test_is_node_not_ready_event_true(self, parser: EventParser) -> None:
        """Test _is_node_not_ready_event identifies node not ready events."""
        assert parser._is_node_not_ready_event("NodeNotReady", "Node") is True
        assert parser._is_node_not_ready_event("NodeNotSchedulable", "Node") is True

    def test_is_node_not_ready_event_false(self, parser: EventParser) -> None:
        """Test _is_node_not_ready_event rejects non-node events."""
        assert parser._is_node_not_ready_event("NodeNotReady", "Pod") is False
        assert parser._is_node_not_ready_event("Scheduled", "Node") is False

    def test_is_scheduling_failure_true(self, parser: EventParser) -> None:
        """Test _is_scheduling_failure identifies scheduling failures."""
        assert parser._is_scheduling_failure("FailedScheduling") is True
        assert parser._is_scheduling_failure("FailedCreate") is True

    def test_is_scheduling_failure_false(self, parser: EventParser) -> None:
        """Test _is_scheduling_failure rejects non-scheduling failures."""
        assert parser._is_scheduling_failure("Scheduled") is False
        assert parser._is_scheduling_failure("Created") is False

    def test_is_backoff_event_true(self, parser: EventParser) -> None:
        """Test _is_backoff_event identifies backoff events."""
        assert parser._is_backoff_event("BackOff", "image pull") is True
        assert parser._is_backoff_event("Failed", "BackOff detected") is True
        assert parser._is_backoff_event("Reason", "BackOff") is True

    def test_is_backoff_event_false(self, parser: EventParser) -> None:
        """Test _is_backoff_event rejects non-backoff events."""
        assert parser._is_backoff_event("Scheduled", "pod scheduled") is False
        assert parser._is_backoff_event("Created", "container created") is False

    def test_is_unhealthy_event_true(self, parser: EventParser) -> None:
        """Test _is_unhealthy_event identifies unhealthy events."""
        assert parser._is_unhealthy_event("Unhealthy") is True

    def test_is_unhealthy_event_false(self, parser: EventParser) -> None:
        """Test _is_unhealthy_event rejects non-unhealthy events."""
        assert parser._is_unhealthy_event("Healthy") is False
        assert parser._is_unhealthy_event("Ready") is False

    def test_is_failed_mount_event_true(self, parser: EventParser) -> None:
        """Test _is_failed_mount_event identifies mount failures."""
        assert parser._is_failed_mount_event("FailedMount") is True
        assert parser._is_failed_mount_event("FailedAttachVolume") is True
        assert parser._is_failed_mount_event("FailedMapVolume") is True

    def test_is_failed_mount_event_false(self, parser: EventParser) -> None:
        """Test _is_failed_mount_event rejects non-mount failures."""
        assert parser._is_failed_mount_event("Scheduled") is False
        assert parser._is_failed_mount_event("Created") is False

    def test_is_eviction_event_true(self, parser: EventParser) -> None:
        """Test _is_eviction_event identifies eviction events."""
        assert parser._is_eviction_event("Evicted", "pod was evicted") is True
        assert parser._is_eviction_event("Preempted", "pod was preempted") is True
        assert parser._is_eviction_event("Reason", "evict pod") is True

    def test_is_eviction_event_false(self, parser: EventParser) -> None:
        """Test _is_eviction_event rejects non-eviction events."""
        assert parser._is_eviction_event("Scheduled", "pod scheduled") is False
        assert parser._is_eviction_event("Created", "pod created") is False

    def test_parse_events_summary_empty(self, parser: EventParser) -> None:
        """Test parse_events_summary with empty events list."""
        result = parser.parse_events_summary([])

        assert result.total_count == 0
        assert result.oom_count == 0
        assert result.recent_events == []

    def test_parse_events_summary_with_oom(self, parser: EventParser) -> None:
        """Test parse_events_summary counts OOM events."""
        now = datetime.now(timezone.utc)
        events = [
            {
                "reason": "OOMKilling",
                "message": "container out of memory",
                "type": "Warning",
                "count": 2,
                "lastTimestamp": now.isoformat(),
                "involvedObject": {"name": "pod1", "kind": "Pod"},
            },
        ]

        result = parser.parse_events_summary(events)

        assert result.oom_count == 2

    def test_parse_events_summary_uses_deprecated_count_field(
        self,
        parser: EventParser,
    ) -> None:
        """deprecatedCount should be used when count is missing."""
        now = datetime.now(timezone.utc)
        events = [
            {
                "reason": "OOMKilling",
                "message": "container out of memory",
                "type": "Warning",
                "deprecatedCount": 3,
                "lastTimestamp": now.isoformat(),
                "involvedObject": {"name": "pod1", "kind": "Pod"},
            },
        ]

        result = parser.parse_events_summary(events)
        assert result.oom_count == 3

    def test_parse_events_summary_filters_old_events(self, parser: EventParser) -> None:
        """Test parse_events_summary filters events older than max_age."""
        now = datetime.now(timezone.utc)
        # Event from 2 hours ago (should be filtered with 1h max_age)
        old_time = (now - timedelta(hours=2)).isoformat()
        events = [
            {
                "reason": "Scheduled",
                "message": "pod scheduled",
                "type": "Normal",
                "count": 1,
                "lastTimestamp": now.isoformat(),
                "involvedObject": {"name": "pod1", "kind": "Pod"},
            },
            {
                "reason": "OOMKilling",
                "message": "OOM",
                "type": "Warning",
                "count": 1,
                "lastTimestamp": old_time,
                "involvedObject": {"name": "pod2", "kind": "Pod"},
            },
        ]

        result = parser.parse_events_summary(events, max_age_hours=1.0)

        # Only the recent event should be counted; old OOM event filtered
        assert result.oom_count == 0

    def test_parse_events_summary_scales_repeated_count_to_event_window(
        self,
        parser: EventParser,
    ) -> None:
        """Repeated event count should be scaled to selected lookback window."""
        now = datetime.now(timezone.utc)
        first_seen = now - timedelta(hours=4)
        events = [
            {
                "reason": "BackOff",
                "message": "Back-off restarting failed container",
                "type": "Warning",
                "count": 400,
                "firstTimestamp": first_seen.isoformat(),
                "lastTimestamp": now.isoformat(),
                "involvedObject": {"name": "pod1", "kind": "Pod"},
            },
        ]

        result = parser.parse_events_summary(events, max_age_hours=0.25)

        # 400 events over 4h -> ~25 events in 15m window.
        assert result.backoff_count == 25

    def test_parse_critical_events_empty(self, parser: EventParser) -> None:
        """Test parse_critical_events with empty events list."""
        result = parser.parse_critical_events([])

        assert result == []

    def test_parse_critical_events_with_critical(self, parser: EventParser) -> None:
        """Test parse_critical_events identifies critical events."""
        now = datetime.now(timezone.utc)
        events = [
            {
                "reason": "OOMKilling",
                "message": "container out of memory",
                "type": "Warning",
                "count": 1,
                "lastTimestamp": now.isoformat(),
                "involvedObject": {"name": "pod1", "namespace": "default", "kind": "Pod"},
                "source": {"component": "kubelet"},
            },
        ]

        result = parser.parse_critical_events(events)

        assert len(result) == 1
        assert result[0].reason == "OOMKilling"

    def test_parse_critical_events_scales_repeated_count_to_event_window(
        self,
        parser: EventParser,
    ) -> None:
        """Critical detail row count should follow selected lookback window."""
        now = datetime.now(timezone.utc)
        first_seen = now - timedelta(hours=2)
        events = [
            {
                "reason": "BackOff",
                "message": "Back-off restarting failed container",
                "type": "Warning",
                "count": 120,
                "firstTimestamp": first_seen.isoformat(),
                "lastTimestamp": now.isoformat(),
                "involvedObject": {"name": "pod1", "namespace": "default", "kind": "Pod"},
            },
        ]

        result = parser.parse_critical_events(events, max_age_hours=0.25)

        assert len(result) == 1
        # 120 events over 2h -> ~15 events in 15m window.
        assert result[0].count == 15

    def test_parse_critical_events_respects_limit(self, parser: EventParser) -> None:
        """Test parse_critical_events respects limit parameter."""
        now = datetime.now(timezone.utc)
        events = [
            {
                "reason": "OOMKilling",
                "message": f"OOM {i}",
                "type": "Warning",
                "count": 1,
                "lastTimestamp": now.isoformat(),
                "involvedObject": {"name": f"pod{i}", "namespace": "default", "kind": "Pod"},
            }
            for i in range(10)
        ]

        result = parser.parse_critical_events(events, limit=5)

        assert len(result) == 5

    def test_parse_events_summary_normalizes_z(self, parser: EventParser) -> None:
        """Test parse_events_summary handles Z suffix in timestamps."""
        now = datetime.now(timezone.utc)
        events = [
            {
                "reason": "Scheduled",
                "message": "pod scheduled",
                "type": "Normal",
                "count": 1,
                "lastTimestamp": now.isoformat().replace("+00:00", "Z"),
                "involvedObject": {"name": "pod1", "kind": "Pod"},
            },
        ]

        result = parser.parse_events_summary(events)

        assert result.total_count == 1
        assert result.normal_count == 1

    def test_parse_events_summary_respects_recent_event_limit(self, parser: EventParser) -> None:
        """Test parse_events_summary respects max_recent_events limit."""
        now = datetime.now(timezone.utc)
        events = [
            {
                "reason": "OOMKilling",
                "message": f"OOM {i}",
                "type": "Warning",
                "count": 1,
                "lastTimestamp": now.isoformat(),
                "involvedObject": {"name": f"pod{i}", "kind": "Pod"},
            }
            for i in range(6)
        ]

        result = parser.parse_events_summary(events, max_recent_events=3)

        assert len(result.recent_events) == 3
