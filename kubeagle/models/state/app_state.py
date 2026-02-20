"""Application state models."""

from kubeagle.constants.enums import AppState as AppStateEnum
from kubeagle.models.analysis.violation import ViolationResult
from kubeagle.models.charts.chart_info import ChartInfo
from kubeagle.models.core.node_info import NodeInfo
from kubeagle.models.pdb.pdb_info import PDBInfo


class AppState:
    """Reactive application state container."""

    def __init__(self) -> None:
        # Connection state
        self.cluster_connected: bool = False
        self.charts_path: str = ""

        # Loading state
        self.loading_state: AppStateEnum = AppStateEnum.IDLE
        self.loading_message: str = ""
        self.error_message: str = ""

        # Cluster data
        self.nodes: list[NodeInfo] = []
        self.events: dict[str, int] = {}  # type -> count
        self.pdbs: list[PDBInfo] = []
        self.single_replica_workloads: list[str] = []

        # Charts data
        self.charts: list[ChartInfo] = []
        self.active_filter: str = "all"
        self.search_query: str = ""

        # Optimizer data
        self.violations: list[ViolationResult] = []
        self.violation_count: int = 0

        # UI state
        self.current_screen: str = "cluster"
        self.selected_node: str | None = None
        self.selected_chart: str | None = None

        # Export data
        self.export_data: str = ""
        self.export_path: str = ""
