"""Init file for cluster fetchers."""

from kubeagle.controllers.cluster.fetchers.cluster_fetcher import (
    ClusterFetcher,
)
from kubeagle.controllers.cluster.fetchers.event_fetcher import (
    EventFetcher,
)
from kubeagle.controllers.cluster.fetchers.node_fetcher import NodeFetcher
from kubeagle.controllers.cluster.fetchers.pod_fetcher import PodFetcher
from kubeagle.controllers.cluster.fetchers.top_metrics_fetcher import (
    TopMetricsFetcher,
)

__all__ = [
    "ClusterFetcher",
    "EventFetcher",
    "NodeFetcher",
    "PodFetcher",
    "TopMetricsFetcher",
]
