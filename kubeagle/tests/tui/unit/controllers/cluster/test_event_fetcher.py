"""Tests for event fetcher."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from kubeagle.constants.timeouts import CLUSTER_REQUEST_TIMEOUT
from kubeagle.controllers.cluster.fetchers.event_fetcher import (
    EventFetcher,
)


class TestEventFetcher:
    """Tests for EventFetcher class."""

    @pytest.fixture
    def mock_run_kubectl(self) -> AsyncMock:
        """Create mock run_kubectl function."""
        return AsyncMock()

    def test_fetcher_init(self, mock_run_kubectl: AsyncMock) -> None:
        """Test EventFetcher initialization with run_kubectl_func."""
        fetcher = EventFetcher(run_kubectl_func=mock_run_kubectl)
        assert fetcher._run_kubectl is mock_run_kubectl

    def test_fetcher_init_default_context(self, mock_run_kubectl: AsyncMock) -> None:
        """Test EventFetcher initialization stores the callable."""
        fetcher = EventFetcher(mock_run_kubectl)
        assert fetcher._run_kubectl is mock_run_kubectl

    @pytest.mark.asyncio
    async def test_fetch_events_summary_uses_warning_query_defaults(
        self,
        mock_run_kubectl: AsyncMock,
    ) -> None:
        """fetch_events_summary should use warning-only chunked query and timeout."""
        mock_run_kubectl.return_value = '{"items": []}'
        fetcher = EventFetcher(mock_run_kubectl)

        result = await fetcher.fetch_events_summary()

        assert result == {
            "oom": 0,
            "node_not_ready": 0,
            "failed_scheduling": 0,
            "backoff": 0,
            "unhealthy": 0,
            "failed_mount": 0,
            "evicted": 0,
        }
        called_args = mock_run_kubectl.await_args_list[0].args[0]
        assert "--field-selector=type=Warning" in called_args
        assert "--chunk-size=200" in called_args
        assert f"--request-timeout={CLUSTER_REQUEST_TIMEOUT}" in called_args

    @pytest.mark.asyncio
    async def test_fetch_events_summary_retries_timeout(
        self,
        mock_run_kubectl: AsyncMock,
    ) -> None:
        """Event fetch should retry timeout failures with longer timeout."""
        mock_run_kubectl.side_effect = [
            RuntimeError("request timed out"),
            '{"items": []}',
        ]
        fetcher = EventFetcher(mock_run_kubectl)

        result = await fetcher.fetch_events_summary()

        assert result["oom"] == 0
        assert mock_run_kubectl.await_count == 2
        second_args = mock_run_kubectl.await_args_list[1].args[0]
        assert "--request-timeout=45s" in second_args

    @pytest.mark.asyncio
    async def test_fetch_events_summary_raises_non_timeout_error(
        self,
        mock_run_kubectl: AsyncMock,
    ) -> None:
        """Non-timeout errors should bubble up."""
        mock_run_kubectl.side_effect = RuntimeError("forbidden")
        fetcher = EventFetcher(mock_run_kubectl)

        with pytest.raises(RuntimeError, match="forbidden"):
            await fetcher.fetch_events_summary()

    @pytest.mark.asyncio
    async def test_fetch_warning_events_raw_for_namespace_uses_namespace_scope(
        self,
        mock_run_kubectl: AsyncMock,
    ) -> None:
        """Namespace-scoped warning fetch should use -n namespace."""
        mock_run_kubectl.return_value = '{"items": []}'
        fetcher = EventFetcher(mock_run_kubectl)

        events = await fetcher.fetch_warning_events_raw(namespace="payments")

        assert events == []
        called_args = mock_run_kubectl.await_args_list[0].args[0]
        assert "--all-namespaces" not in called_args
        assert "-n" in called_args
        ns_index = called_args.index("-n")
        assert called_args[ns_index + 1] == "payments"

    @pytest.mark.asyncio
    async def test_fetch_events_summary_scales_repeated_count_to_event_window(
        self,
        mock_run_kubectl: AsyncMock,
    ) -> None:
        """Repeated warning event count should be scaled to selected lookback."""
        now = datetime.now(timezone.utc)
        first_seen = now - timedelta(hours=4)
        mock_run_kubectl.return_value = json.dumps(
            {
                "items": [
                    {
                        "reason": "BackOff",
                        "message": "Back-off restarting failed container",
                        "type": "Warning",
                        "count": 400,
                        "firstTimestamp": first_seen.isoformat(),
                        "lastTimestamp": now.isoformat(),
                        "involvedObject": {"kind": "Pod", "name": "pod1"},
                    }
                ]
            }
        )
        fetcher = EventFetcher(mock_run_kubectl)

        result = await fetcher.fetch_events_summary(max_age_hours=0.25)

        assert result["backoff"] == 25
