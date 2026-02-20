"""Report data models."""

from pydantic import BaseModel

from kubeagle.models.analysis.violation import ViolationResult
from kubeagle.models.charts.chart_info import ChartInfo
from kubeagle.models.core.node_info import NodeInfo
from kubeagle.models.core.workload_info import SingleReplicaWorkloadInfo
from kubeagle.models.events.event_summary import EventSummary
from kubeagle.models.pdb.pdb_info import PDBInfo


class ReportData(BaseModel):
    """Container for all data needed for report generation."""

    # Cluster data
    nodes: list[NodeInfo]
    event_summary: EventSummary | None
    pdbs: list[PDBInfo]
    single_replica_workloads: list[SingleReplicaWorkloadInfo]

    # Charts data
    charts: list[ChartInfo]
    violations: list[ViolationResult]

    # Metadata
    cluster_name: str
    context: str | None
    timestamp: str
