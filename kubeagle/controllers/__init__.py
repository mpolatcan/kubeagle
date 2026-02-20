"""Controllers module for KubEagle TUI.

This module provides domain-driven controllers for fetching and analyzing
Kubernetes cluster data and Helm charts.

## Backward Compatibility

All public APIs are re-exported from this module for backward compatibility.
"""

from __future__ import annotations

# Analyzers
from kubeagle.controllers.analyzers import (
    DistributionAnalyzer,
    EventAnalyzer,
    PDBAnalyzer,
    _get_label_value,
    analyze_blocking_pdbs,
    count_events_by_category,
)

# Re-export label constants for backward compatibility
from kubeagle.controllers.analyzers.distribution_analyzer import (
    _AZ_LABELS,
    _INSTANCE_TYPE_LABELS,
    _NODE_GROUP_LABELS,
    _UNKNOWN_LABEL,
)

# Base classes
from kubeagle.controllers.base import (
    AsyncControllerMixin,
    BaseController,
    LoadingProgress,
    WorkerResult,
)

# Charts domain
from kubeagle.controllers.charts.controller import ChartsController

# Cluster domain
from kubeagle.controllers.cluster.controller import (
    ClusterController,
    FetchStatus,
)

# Team domain
from kubeagle.controllers.team.controller import TeamController
from kubeagle.controllers.team.mappers import TeamInfo, TeamMapper

# Optimizer (import from new location in models/optimization)
from kubeagle.models.optimization import OptimizerController

__all__ = [
    # Base
    "AsyncControllerMixin",
    "BaseController",
    "LoadingProgress",
    "WorkerResult",
    # Domain Controllers
    "ChartsController",
    "ClusterController",
    "TeamController",
    # Cluster domain
    "FetchStatus",
    # Analyzers
    "DistributionAnalyzer",
    "EventAnalyzer",
    "PDBAnalyzer",
    "_get_label_value",
    "analyze_blocking_pdbs",
    "count_events_by_category",
    # Team mappers
    "TeamInfo",
    "TeamMapper",
    # Optimizer
    "OptimizerController",
    # Label constants
    "_AZ_LABELS",
    "_INSTANCE_TYPE_LABELS",
    "_NODE_GROUP_LABELS",
    "_UNKNOWN_LABEL",
]
