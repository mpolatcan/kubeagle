"""Tests for targeted workload live usage sampling in ClusterController."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from kubeagle.controllers.cluster.controller import ClusterController


@pytest.fixture
def controller() -> ClusterController:
    return ClusterController(context="my-cluster")


@pytest.mark.asyncio
async def test_fetch_workload_live_usage_sample_aggregates_targeted_metrics(
    controller: ClusterController,
) -> None:
    pods = [
        {
            "metadata": {
                "namespace": "team-a",
                "name": "api-1",
                "ownerReferences": [
                    {"kind": "Deployment", "name": "api", "controller": True}
                ],
            },
            "spec": {"nodeName": "node-a"},
        },
        {
            "metadata": {
                "namespace": "team-a",
                "name": "api-2",
                "ownerReferences": [
                    {"kind": "Deployment", "name": "api", "controller": True}
                ],
            },
            "spec": {"nodeName": "node-b"},
        },
        {
            "metadata": {
                "namespace": "team-a",
                "name": "other-1",
                "ownerReferences": [
                    {"kind": "Deployment", "name": "other", "controller": True}
                ],
            },
            "spec": {"nodeName": "node-c"},
        },
    ]
    controller._pod_fetcher.fetch_pods_for_namespace = AsyncMock(  # type: ignore[method-assign]
        return_value=pods
    )
    controller._top_metrics_fetcher.fetch_top_pods_for_namespace = AsyncMock(  # type: ignore[method-assign]
        return_value=[
            {
                "namespace": "team-a",
                "pod_name": "api-1",
                "cpu_mcores": 110.0,
                "memory_bytes": 220.0,
            }
        ]
    )
    controller._top_metrics_fetcher.fetch_top_nodes_for_names = AsyncMock(  # type: ignore[method-assign]
        return_value=[
            {"node_name": "node-a", "cpu_mcores": 1000.0, "memory_bytes": 2000.0}
        ]
    )
    controller._top_metrics_fetcher.fetch_top_pods_all_namespaces = AsyncMock()  # type: ignore[method-assign]

    sample = await controller.fetch_workload_live_usage_sample(
        "team-a",
        "Deployment",
        "api",
    )

    assert sample.namespace == "team-a"
    assert sample.workload_kind == "Deployment"
    assert sample.workload_name == "api"
    assert sample.pod_count == 2
    assert sample.node_count == 2
    assert sample.pods_with_metrics == 1
    assert sample.nodes_with_metrics == 1
    assert sample.workload_cpu_mcores == pytest.approx(110.0)
    assert sample.workload_memory_bytes == pytest.approx(220.0)
    controller._top_metrics_fetcher.fetch_top_pods_for_namespace.assert_awaited_once()
    controller._top_metrics_fetcher.fetch_top_nodes_for_names.assert_awaited_once()
    controller._top_metrics_fetcher.fetch_top_pods_all_namespaces.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_workload_live_usage_sample_returns_empty_when_no_workload_pods(
    controller: ClusterController,
) -> None:
    controller._pod_fetcher.fetch_pods_for_namespace = AsyncMock(  # type: ignore[method-assign]
        return_value=[]
    )
    controller._top_metrics_fetcher.fetch_top_pods_for_namespace = AsyncMock()  # type: ignore[method-assign]
    controller._top_metrics_fetcher.fetch_top_nodes_for_names = AsyncMock()  # type: ignore[method-assign]

    sample = await controller.fetch_workload_live_usage_sample(
        "team-a",
        "Deployment",
        "api",
    )

    assert sample.pod_count == 0
    assert sample.node_count == 0
    assert sample.workload_cpu_mcores is None
    assert sample.workload_memory_bytes is None
    controller._top_metrics_fetcher.fetch_top_pods_for_namespace.assert_not_called()
    controller._top_metrics_fetcher.fetch_top_nodes_for_names.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_workload_live_usage_sample_handles_invalid_identity(
    controller: ClusterController,
) -> None:
    controller._pod_fetcher.fetch_pods_for_namespace = AsyncMock()  # type: ignore[method-assign]

    sample = await controller.fetch_workload_live_usage_sample(
        "",
        "",
        "",
    )

    assert sample.namespace == ""
    assert sample.workload_kind == ""
    assert sample.workload_name == ""
    assert sample.workload_cpu_mcores is None
    assert sample.workload_memory_bytes is None
    controller._pod_fetcher.fetch_pods_for_namespace.assert_not_called()
