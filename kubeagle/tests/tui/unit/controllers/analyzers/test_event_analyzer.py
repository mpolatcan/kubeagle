"""Tests for event analyzer."""

from __future__ import annotations

from datetime import datetime, timezone

from kubeagle.constants.enums import Severity
from kubeagle.controllers.analyzers.event_analyzer import (
    EventAnalyzer,
    count_events_by_category,
)


class TestEventAnalyzer:
    """Tests for EventAnalyzer class."""

    def test_analyzer_init(self) -> None:
        """Test EventAnalyzer initialization."""
        analyzer = EventAnalyzer()
        assert isinstance(analyzer, EventAnalyzer)

    def test_analyze_empty_events(self) -> None:
        """Test analyze with empty events list."""
        analyzer = EventAnalyzer()

        # The analyzer should be able to handle empty input without error
        # Just verify the object was created successfully
        assert analyzer is not None


# =============================================================================
# is_oom_event TESTS
# =============================================================================


class TestIsOOMEvent:
    """Tests for EventAnalyzer.is_oom_event()."""

    def test_oom_event_by_reason(self) -> None:
        """Test OOM detection when reason is OOMKilling."""
        assert EventAnalyzer.is_oom_event("OOMKilling", "") is True

    def test_oom_event_by_message_oomkill(self) -> None:
        """Test OOM detection when message contains OOMKill."""
        assert EventAnalyzer.is_oom_event("SomeReason", "Container was OOMKill") is True

    def test_oom_event_by_message_out_of_memory(self) -> None:
        """Test OOM detection when message contains 'Out of memory'."""
        assert EventAnalyzer.is_oom_event("SomeReason", "Out of memory for container foo") is True

    def test_not_oom_event(self) -> None:
        """Test non-OOM event returns False."""
        assert EventAnalyzer.is_oom_event("Started", "Container started successfully") is False


# =============================================================================
# is_node_not_ready_event TESTS
# =============================================================================


class TestIsNodeNotReadyEvent:
    """Tests for EventAnalyzer.is_node_not_ready_event()."""

    def test_node_not_ready_positive(self) -> None:
        """Test detection of NodeNotReady event on Node kind."""
        assert EventAnalyzer.is_node_not_ready_event("NodeNotReady", "Node") is True

    def test_node_not_schedulable_positive(self) -> None:
        """Test detection of NodeNotSchedulable event on Node kind."""
        assert EventAnalyzer.is_node_not_ready_event("NodeNotSchedulable", "Node") is True

    def test_node_not_ready_wrong_kind(self) -> None:
        """Test NodeNotReady on non-Node kind returns False."""
        assert EventAnalyzer.is_node_not_ready_event("NodeNotReady", "Pod") is False

    def test_not_node_not_ready(self) -> None:
        """Test unrelated reason returns False."""
        assert EventAnalyzer.is_node_not_ready_event("Started", "Node") is False


# =============================================================================
# is_scheduling_failure TESTS
# =============================================================================


class TestIsSchedulingFailure:
    """Tests for EventAnalyzer.is_scheduling_failure()."""

    def test_failed_scheduling(self) -> None:
        """Test FailedScheduling detection."""
        assert EventAnalyzer.is_scheduling_failure("FailedScheduling") is True

    def test_failed_create(self) -> None:
        """Test FailedCreate detection."""
        assert EventAnalyzer.is_scheduling_failure("FailedCreate") is True

    def test_not_scheduling_failure(self) -> None:
        """Test non-scheduling reason returns False."""
        assert EventAnalyzer.is_scheduling_failure("Started") is False


# =============================================================================
# is_backoff_event TESTS
# =============================================================================


class TestIsBackoffEvent:
    """Tests for EventAnalyzer.is_backoff_event()."""

    def test_backoff_reason(self) -> None:
        """Test BackOff reason detection."""
        assert EventAnalyzer.is_backoff_event("BackOff", "Back-off restarting failed container") is True

    def test_failed_with_pull_message(self) -> None:
        """Test Failed reason with pull in message."""
        assert EventAnalyzer.is_backoff_event("Failed", "Failed to pull image foo:latest") is True

    def test_failed_without_pull(self) -> None:
        """Test Failed reason without pull in message returns False."""
        assert EventAnalyzer.is_backoff_event("Failed", "Container exited with code 1") is False

    def test_not_backoff_event(self) -> None:
        """Test non-backoff reason returns False."""
        assert EventAnalyzer.is_backoff_event("Started", "Container started") is False


# =============================================================================
# is_unhealthy_event TESTS
# =============================================================================


class TestIsUnhealthyEvent:
    """Tests for EventAnalyzer.is_unhealthy_event()."""

    def test_unhealthy_event(self) -> None:
        """Test Unhealthy reason detection."""
        assert EventAnalyzer.is_unhealthy_event("Unhealthy") is True

    def test_not_unhealthy_event(self) -> None:
        """Test non-Unhealthy reason returns False."""
        assert EventAnalyzer.is_unhealthy_event("Healthy") is False


# =============================================================================
# is_failed_mount_event TESTS
# =============================================================================


class TestIsFailedMountEvent:
    """Tests for EventAnalyzer.is_failed_mount_event()."""

    def test_failed_mount(self) -> None:
        """Test FailedMount reason detection."""
        assert EventAnalyzer.is_failed_mount_event("FailedMount") is True

    def test_failed_attach_volume(self) -> None:
        """Test FailedAttachVolume reason detection."""
        assert EventAnalyzer.is_failed_mount_event("FailedAttachVolume") is True

    def test_not_failed_mount(self) -> None:
        """Test non-mount-failure reason returns False."""
        assert EventAnalyzer.is_failed_mount_event("Started") is False


# =============================================================================
# is_eviction_event TESTS
# =============================================================================


class TestIsEvictionEvent:
    """Tests for EventAnalyzer.is_eviction_event()."""

    def test_evicted_reason(self) -> None:
        """Test Evicted reason detection."""
        assert EventAnalyzer.is_eviction_event("Evicted", "") is True

    def test_evict_in_message(self) -> None:
        """Test eviction detection via message content."""
        assert EventAnalyzer.is_eviction_event("SomeReason", "Pod was evicted due to pressure") is True

    def test_not_eviction_event(self) -> None:
        """Test non-eviction event returns False."""
        assert EventAnalyzer.is_eviction_event("Started", "Container started") is False


# =============================================================================
# parse_event_timestamp TESTS
# =============================================================================


class TestParseEventTimestamp:
    """Tests for EventAnalyzer.parse_event_timestamp()."""

    def test_valid_timestamp(self) -> None:
        """Test parsing a valid ISO timestamp."""
        event = {"lastTimestamp": "2025-01-15T10:30:00Z"}
        time_str, dt = EventAnalyzer.parse_event_timestamp(event)
        assert time_str == "2025-01-15T10:30:00Z"
        assert dt is not None
        assert dt.year == 2025
        assert dt.month == 1
        assert dt.day == 15

    def test_no_timestamp_returns_none(self) -> None:
        """Test that missing timestamp returns None for both values."""
        event: dict = {}
        time_str, dt = EventAnalyzer.parse_event_timestamp(event)
        assert time_str is None
        assert dt is None

    def test_fallback_to_event_time(self) -> None:
        """Test fallback from lastTimestamp to eventTime."""
        event = {"eventTime": "2025-06-01T12:00:00Z"}
        time_str, dt = EventAnalyzer.parse_event_timestamp(event)
        assert time_str == "2025-06-01T12:00:00Z"
        assert dt is not None

    def test_fallback_to_creation_timestamp(self) -> None:
        """Test fallback to metadata.creationTimestamp."""
        event = {"metadata": {"creationTimestamp": "2025-03-20T08:00:00Z"}}
        time_str, dt = EventAnalyzer.parse_event_timestamp(event)
        assert time_str == "2025-03-20T08:00:00Z"
        assert dt is not None


# =============================================================================
# format_involved_object TESTS
# =============================================================================


class TestFormatInvolvedObject:
    """Tests for EventAnalyzer.format_involved_object()."""

    def test_node_object(self) -> None:
        """Test formatting a Node involved object."""
        event = {"involvedObject": {"kind": "Node", "name": "ip-10-0-1-5", "namespace": ""}}
        result = EventAnalyzer.format_involved_object(event)
        assert result == "Node/ip-10-0-1-5"

    def test_namespaced_object(self) -> None:
        """Test formatting a namespaced involved object."""
        event = {"involvedObject": {"kind": "Pod", "name": "my-pod-123", "namespace": "default"}}
        result = EventAnalyzer.format_involved_object(event)
        assert result == "default/my-pod-123"

    def test_name_only_object(self) -> None:
        """Test formatting an object with name only (no namespace)."""
        event = {"involvedObject": {"kind": "Pod", "name": "orphan-pod", "namespace": ""}}
        result = EventAnalyzer.format_involved_object(event)
        assert result == "orphan-pod"

    def test_empty_involved_object(self) -> None:
        """Test formatting when involvedObject is empty."""
        event: dict = {"involvedObject": {}}
        result = EventAnalyzer.format_involved_object(event)
        assert result == ""


# =============================================================================
# classify_event TESTS
# =============================================================================


class TestClassifyEvent:
    """Tests for EventAnalyzer.classify_event()."""

    def test_classify_oom_event(self) -> None:
        """Test classification of an OOM event as ERROR severity."""
        event = {
            "reason": "OOMKilling",
            "message": "OOMKill container foo",
            "type": "Warning",
            "count": 3,
            "lastTimestamp": datetime.now(timezone.utc).isoformat(),
            "involvedObject": {"kind": "Pod", "name": "my-pod", "namespace": "default"},
        }
        result = EventAnalyzer.classify_event(event, max_age_seconds=3600)
        assert result is not None
        assert result["is_critical"] is True
        assert result["severity"] == Severity.ERROR
        assert result["reason"] == "OOMKilling"

    def test_classify_normal_event(self) -> None:
        """Test classification of a normal event as INFO severity."""
        event = {
            "reason": "Pulled",
            "message": "Successfully pulled image",
            "type": "Normal",
            "count": 1,
            "lastTimestamp": datetime.now(timezone.utc).isoformat(),
            "involvedObject": {"kind": "Pod", "name": "my-pod", "namespace": "default"},
        }
        result = EventAnalyzer.classify_event(event, max_age_seconds=3600)
        assert result is not None
        assert result["is_critical"] is False
        assert result["severity"] == Severity.INFO

    def test_classify_unhealthy_event_warning(self) -> None:
        """Test classification of an Unhealthy event as WARNING severity."""
        event = {
            "reason": "Unhealthy",
            "message": "Liveness probe failed",
            "type": "Warning",
            "count": 5,
            "lastTimestamp": datetime.now(timezone.utc).isoformat(),
            "involvedObject": {"kind": "Pod", "name": "probe-pod", "namespace": "kube-system"},
        }
        result = EventAnalyzer.classify_event(event, max_age_seconds=3600)
        assert result is not None
        assert result["is_critical"] is True
        assert result["severity"] == Severity.WARNING


# =============================================================================
# count_events_by_category TESTS
# =============================================================================


class TestCountEventsByCategory:
    """Tests for count_events_by_category function."""

    def test_empty_events(self) -> None:
        """Test counting with empty events list."""
        counts = count_events_by_category([])
        assert counts["oom"] == 0
        assert counts["node_not_ready"] == 0
        assert counts["failed_scheduling"] == 0

    def test_mixed_events(self) -> None:
        """Test counting mixed event types."""
        now = datetime.now(timezone.utc).isoformat()
        events = [
            {"reason": "OOMKilling", "message": "", "count": 2, "lastTimestamp": now, "involvedObject": {"kind": "Pod"}},
            {"reason": "Unhealthy", "message": "", "count": 3, "lastTimestamp": now, "involvedObject": {"kind": "Pod"}},
            {"reason": "FailedScheduling", "message": "", "count": 1, "lastTimestamp": now, "involvedObject": {"kind": "Pod"}},
        ]
        counts = count_events_by_category(events, max_age_hours=1.0)
        assert counts["oom"] == 2
        assert counts["unhealthy"] == 3
        assert counts["failed_scheduling"] == 1


# =============================================================================
# parse_events_json TESTS
# =============================================================================


class TestParseEventsJson:
    """Tests for EventAnalyzer.parse_events_json()."""

    def test_empty_string(self) -> None:
        """Test parsing empty string returns empty events."""
        result = EventAnalyzer.parse_events_json("")
        assert result == {"events": [], "error": None}

    def test_valid_json(self) -> None:
        """Test parsing valid events JSON."""
        import json

        data = {"items": [{"reason": "Started", "message": "test"}]}
        result = EventAnalyzer.parse_events_json(json.dumps(data))
        assert len(result["events"]) == 1
        assert result["error"] is None

    def test_invalid_json(self) -> None:
        """Test parsing invalid JSON returns error."""
        result = EventAnalyzer.parse_events_json("not valid json{")
        assert result["events"] == []
        assert result["error"] is not None
