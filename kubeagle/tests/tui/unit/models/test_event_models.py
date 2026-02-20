"""Tests for event models."""

from __future__ import annotations

from kubeagle.models.events.event_info import EventDetail
from kubeagle.models.events.event_summary import EventSummary


class TestEventDetail:
    """Tests for EventDetail model."""

    def test_event_detail_creation(self) -> None:
        """Test EventDetail creation."""
        event = EventDetail(
            type="Warning",
            reason="OOMKilling",
            message="container out of memory",
            count=2,
            last_timestamp="2024-01-15T10:30:00Z",
            source="kubelet",
            involved_object="default/my-pod",
            severity="error",
        )

        assert event.type == "Warning"
        assert event.reason == "OOMKilling"
        assert event.count == 2
        assert event.severity == "error"


class TestEventSummary:
    """Tests for EventSummary model."""

    def test_event_summary_creation(self) -> None:
        """Test EventSummary creation."""
        summary = EventSummary(
            total_count=10,
            oom_count=2,
            node_not_ready_count=1,
            failed_scheduling_count=3,
            backoff_count=1,
            unhealthy_count=1,
            failed_mount_count=1,
            evicted_count=0,
            completed_count=1,
            normal_count=0,
            recent_events=[],
            max_age_hours=1.0,
            desired_healthy=5,
        )

        assert summary.total_count == 10
        assert summary.oom_count == 2
        assert summary.desired_healthy == 5

    def test_event_summary_with_recent_events(self) -> None:
        """Test EventSummary with recent events."""
        recent_events = [
            {
                "type": "Warning",
                "reason": "OOMKilling",
                "message": "container out of memory",
                "count": "2",
                "last_timestamp": "2024-01-15T10:30:00Z",
                "involved_object": "default/my-pod",
            }
        ]

        summary = EventSummary(
            total_count=2,
            oom_count=2,
            node_not_ready_count=0,
            failed_scheduling_count=0,
            backoff_count=0,
            unhealthy_count=0,
            failed_mount_count=0,
            evicted_count=0,
            completed_count=0,
            normal_count=0,
            recent_events=recent_events,
            max_age_hours=1.0,
            desired_healthy=3,
        )

        assert len(summary.recent_events) == 1
        assert summary.recent_events[0]["reason"] == "OOMKilling"
