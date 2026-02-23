# Data Flow

This document describes how data flows through the KubEagle TUI application, from external sources to screen rendering.

## Overview

```mermaid
graph TB
    subgraph Sources["Data Sources"]
        Helm["Helm Charts (YAML)"]
        EKS["EKS Cluster (kubectl)"]
        CODEOWNERS["CODEOWNERS"]
    end

    subgraph Controllers["Controllers"]
        ChartsCtrl["ChartsController<br/>analyze_all_charts<br/>get_team_statistics"]
        ClusterCtrl["ClusterController<br/>fetch_nodes<br/>fetch_events<br/>fetch_pdbs"]
        TeamCtrl["Team Module<br/>get_team_info<br/>map_chart_team"]
    end

    subgraph OptimizerMod["Optimizer Module"]
        Analyzer["analyzer.py"]
        Fixer["fixer.py"]
        Rules["rules.py"]
        AIFixer["full_ai_fixer.py"]
    end

    subgraph Models["Models (Pydantic)"]
        ChartInfo
        NodeInfo["NodeInfo, EventSummary"]
        PDBInfo["PDBInfo, BlockingPDB"]
        TeamInfo["TeamInfo, TeamStatistics"]
        OptViolation["OptimizationViolation"]
    end

    subgraph Screens["Screens (7)"]
        ClusterScreen
        ChartsExplorerScreen
        WorkloadsScreen
        OptimizerScreen
        ChartDetailScreen
        SettingsScreen
        ReportExportScreen
    end

    subgraph Widgets["Widgets"]
        CustomDataTable
        CustomKPI
        CustomCard
        CustomFooter
    end

    Helm --> ChartsCtrl
    Helm --> OptimizerMod
    EKS --> ClusterCtrl
    CODEOWNERS --> TeamCtrl

    ChartsCtrl --> ChartInfo
    ClusterCtrl --> NodeInfo
    ClusterCtrl --> PDBInfo
    TeamCtrl --> TeamInfo
    OptimizerMod --> OptViolation

    ChartInfo --> ChartsExplorerScreen
    ChartInfo --> ChartDetailScreen
    NodeInfo --> ClusterScreen
    PDBInfo --> ClusterScreen
    TeamInfo --> ChartsExplorerScreen
    OptViolation --> OptimizerScreen
    OptViolation --> ChartsExplorerScreen

    Screens --> Widgets
```

## Data Loading Lifecycle

### 1. Application Startup

```python
# main.py - CLI entry point
def main(charts_path: Path, skip_eks: bool, ...):
    app = EKSHelmReporterApp(
        charts_path=charts_path,
        skip_eks=skip_eks,
        ...
    )
    app.run()
```

### 2. App Initialization

```python
# app.py
class EKSHelmReporterApp(App[None]):
    def __init__(self, charts_path: Path | None, skip_eks: bool, ...):
        super().__init__()
        self.charts_path = charts_path
        self.skip_eks = skip_eks
        self.state = AppState()
        register_kubeagle_themes(self)  # Register custom themes
        self._load_settings()           # Load + normalize paths + apply theme + apply optimizer thresholds

    def on_mount(self) -> None:
        """Called when app is mounted."""
        from kubeagle.screens import ClusterScreen
        self._activate_installed_screen(self._SCREEN_CLUSTER_NAME, ClusterScreen)
        self.call_after_refresh(self._enforce_terminal_size_policy)
```

### 3. Screen Data Loading (Worker Pattern)

```mermaid
sequenceDiagram
    participant App
    participant Screen as ClusterScreen
    participant Worker
    participant Controller as ClusterController
    participant UI as Widgets

    App->>Screen: push_screen / activate
    Screen->>Screen: on_mount()
    Screen->>Worker: start_worker(_load_cluster_data)
    Worker->>Controller: fetch_nodes()
    Worker->>Controller: get_event_summary()
    Worker->>Controller: fetch_pdbs()
    Note over Controller: asyncio.gather for concurrency
    Controller-->>Worker: nodes, events, pdbs
    Worker->>Screen: self.data = {nodes, events, pdbs}
    Screen->>Screen: watch_data(data)
    Screen->>UI: _update_tables(data)
    Screen->>UI: _update_summary(data)
    Worker->>Screen: self.is_loading = False
```

```python
# screens/cluster/cluster_screen.py
class ClusterScreen(BaseScreen, WorkerMixin, TabbedViewMixin):
    """Cluster health monitoring screen."""

    is_loading = reactive(False)
    data = reactive[dict]({})
    error = reactive[str | None](None)

    def on_mount(self) -> None:
        """Start data loading when screen mounts."""
        self.start_worker(self._load_cluster_data)

    @work(exclusive=True)
    async def _load_cluster_data(self) -> None:
        """Load cluster data in background worker."""
        self.is_loading = True
        self.error = None

        try:
            controller = ClusterController(context=self.app.context)

            # Fetch data from multiple sources concurrently
            nodes, events, pdbs = await asyncio.gather(
                controller.fetch_nodes(),
                controller.get_event_summary(),
                controller.fetch_pdbs(),
            )

            self.data = {
                "nodes": nodes,
                "events": events,
                "pdbs": pdbs,
            }

        except Exception as e:
            self.error = str(e)
            self.app.notify(f"Error loading data: {e}", severity="error")

        finally:
            self.is_loading = False

    def watch_data(self, data: dict) -> None:
        """React to data changes - update UI."""
        if data:
            self._update_tables(data)
            self._update_summary(data)
```

## Controller Data Fetching

### ChartsController Flow

```python
# controllers/charts/controller.py
class ChartsController(BaseController):
    """Controller for Helm chart analysis."""

    async def analyze_all_charts_async(self) -> list[ChartInfo]:
        """Analyze all charts asynchronously."""
        charts = []

        # Use ThreadPoolExecutor for file I/O
        with ThreadPoolExecutor() as executor:
            futures = []
            for chart_dir in self.charts_path.iterdir():
                if chart_dir.is_dir():
                    futures.append(
                        executor.submit(self._analyze_chart, chart_dir)
                    )

            for future in as_completed(futures):
                if result := future.result():
                    charts.append(result)

        return charts

    def _analyze_chart(self, chart_dir: Path) -> ChartInfo | None:
        """Analyze a single chart directory."""
        values_file = chart_dir / "values.yaml"
        if not values_file.exists():
            return None

        with open(values_file) as f:
            values = yaml.safe_load(f)

        return ChartInfo(
            name=chart_dir.name,
            team=self._get_team(chart_dir),
            values_file="values.yaml",
            cpu_request=self._parse_cpu(values),
            cpu_limit=self._parse_cpu_limit(values),
            # ... more fields
        )
```

### ClusterController Flow

```python
# controllers/cluster/controller.py
class ClusterController(BaseController):
    """Controller for EKS cluster data."""

    async def fetch_nodes(self) -> list[NodeInfo]:
        """Fetch node information from cluster."""
        async with self.bounded_operation():
            result = await asyncio.create_subprocess_exec(
                "kubectl", "get", "nodes", "-o", "json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()

            if result.returncode != 0:
                raise ClusterError(f"kubectl failed: {stderr.decode()}")

            data = json.loads(stdout.decode())
            return [self._parse_node(item) for item in data["items"]]

    def _parse_node(self, item: dict) -> NodeInfo:
        """Parse kubectl node output to NodeInfo."""
        return NodeInfo(
            name=item["metadata"]["name"],
            status=self._get_status(item),
            node_group=self._get_node_group(item),
            instance_type=self._get_instance_type(item),
            # ... more fields
        )
```

## Optimizer Data Flow

The optimizer module operates independently from controllers, analyzing chart values and generating fixes. It supports two fix pipelines: standard (rule-based) and AI (LLM-assisted).

```mermaid
graph TB
    subgraph Input
        Charts["Helm Charts (values.yaml)"]
        Templates["Helm Templates (*.yaml)"]
        RulesFile["rules.py (17 Optimization Rules)"]
        Settings["AppSettings<br/>limit_request_ratio_threshold: 2.0<br/>verify_fixes_with_render: true<br/>ai_fix_llm_provider: codex|claude"]
    end

    subgraph Analysis["Analysis Phase"]
        Analyzer["analyzer.py<br/>ChartAnalyzer<br/>Rule-based violation detection"]
        RenderedInput["rendered_rule_input.py<br/>build_rule_inputs_from_rendered()<br/>Manifest-to-rule-input conversion"]
    end

    subgraph StandardFix["Standard Fix Pipeline"]
        Fixer["fixer.py<br/>FixGenerator<br/>Generate YAML patches"]
    end

    subgraph AIFix["AI Full Fix Pipeline"]
        AIFixer["full_ai_fixer.py<br/>LLM-driven values+template fix"]
        LLMRunner["llm_cli_runner.py<br/>LLMProvider: Codex | Claude<br/>run_llm_direct_edit()"]
        PatchProtocol["llm_patch_protocol.py<br/>StructuredPatchResponse<br/>FullFixResponse"]
        PatchSuggester["template_patch_suggester.py<br/>Wiring hint suggestions"]
    end

    subgraph Verification["Verification & Application"]
        Verifier["fix_verifier.py<br/>FixVerificationResult<br/>FullFixBundleVerificationResult"]
        HelmRenderer["helm_renderer.py<br/>render_chart()<br/>HelmRenderResult"]
        Applier["full_fix_applier.py<br/>apply_full_fix_bundle_atomic()<br/>Thread-safe, atomic writes"]
        WiringDiag["wiring_diagnoser.py<br/>diagnose_template_wiring()"]
    end

    subgraph Output
        Violations["OptimizationViolation"]
        FixedYAML["Fixed values.yaml + templates"]
    end

    Charts --> Analyzer
    Templates --> RenderedInput
    RulesFile --> Analyzer
    Settings --> Analyzer
    RenderedInput --> Analyzer
    Analyzer --> Violations

    Violations --> Fixer
    Violations --> AIFixer
    AIFixer --> LLMRunner
    LLMRunner --> PatchProtocol
    AIFixer --> PatchSuggester

    Fixer --> Verifier
    AIFixer --> Verifier
    Verifier --> HelmRenderer
    Verifier --> Applier
    Verifier --> WiringDiag
    WiringDiag --> PatchSuggester
    Applier --> FixedYAML
```

## AI Full Fix Pipeline Data Flow

The AI Full Fix pipeline is the most complex data flow in the optimizer. It generates values + template patches using LLM providers, applies them atomically, and verifies the result with Helm rendering.

```mermaid
sequenceDiagram
    participant User
    participant Screen as ChartsExplorerScreen
    participant Modal as AIFullFixModal
    participant FullAIFixer as full_ai_fixer.py
    participant LLMRunner as llm_cli_runner.py
    participant PatchProtocol as llm_patch_protocol.py
    participant FixApplier as full_fix_applier.py
    participant FixVerifier as fix_verifier.py
    participant HelmRenderer as helm_renderer.py
    participant WiringDiagnoser as wiring_diagnoser.py

    User->>Screen: Trigger AI Full Fix (via modal)
    Screen->>Modal: push AIFullFixModal(violations, chart_dir)

    Note over Modal, FullAIFixer: Phase 1: LLM Generation
    Modal->>FullAIFixer: generate_full_fix(violations, chart_dir, provider)
    FullAIFixer->>FullAIFixer: Prepare workspace (temp copy of chart)
    FullAIFixer->>LLMRunner: run_llm_direct_edit(prompt, workspace_dir)
    LLMRunner->>LLMRunner: Select Codex or Claude CLI
    LLMRunner->>LLMRunner: Execute non-interactive CLI
    LLMRunner-->>FullAIFixer: LLMDirectEditResult (modified files)
    FullAIFixer->>FullAIFixer: Diff workspace against original
    FullAIFixer->>PatchProtocol: Parse FullFixResponse from diff
    PatchProtocol-->>FullAIFixer: FullFixResponse{values_yaml, template_patches, coverage}

    Note over FullAIFixer, FixApplier: Phase 2: Atomic Application
    FullAIFixer->>FixApplier: apply_full_fix_bundle_atomic(chart_dir, values, patches)
    FixApplier->>FixApplier: Chart-level lock (thread-safe)
    FixApplier->>FixApplier: Backup original files
    FixApplier->>FixApplier: Write new values.yaml + apply template diffs
    FixApplier-->>FullAIFixer: FullFixApplyResult{ok, touched_files}

    Note over FullAIFixer, HelmRenderer: Phase 3: Verification
    FullAIFixer->>FixVerifier: verify_full_fix_bundle(chart_dir, violations)
    FixVerifier->>HelmRenderer: render_chart(chart_dir, values) [BEFORE]
    HelmRenderer-->>FixVerifier: HelmRenderResult (pre-fix manifests)
    FixVerifier->>HelmRenderer: render_chart(chart_dir, values) [AFTER]
    HelmRenderer-->>FixVerifier: HelmRenderResult (post-fix manifests)
    FixVerifier->>FixVerifier: Compare rendered rule inputs before/after
    alt Violation still present
        FixVerifier->>WiringDiagnoser: diagnose_template_wiring(chart_dir, fix)
        WiringDiagnoser-->>FixVerifier: Wiring diagnosis (unmatched keys, candidates)
    end
    FixVerifier-->>FullAIFixer: FullFixBundleVerificationResult{status, per_violation}

    FullAIFixer-->>Modal: Complete result
    Modal-->>Screen: AIFullFixModalResult
    Screen-->>User: Display result + verification status
```

## Workloads Screen Data Flow

The WorkloadsScreen uses `WorkloadsPresenter` for data loading, with progressive partial updates via `WorkloadsSourceLoaded` messages.

```mermaid
sequenceDiagram
    participant Screen as WorkloadsScreen
    participant Presenter as WorkloadsPresenter
    participant Controller as ClusterController
    participant Fetchers as Fetchers (Pod, Node, Event, TopMetrics)
    participant Utils as Utils (cluster_summary)
    participant UI as Widgets (Tables, KPIs)

    Screen->>Screen: on_mount()
    Screen->>Presenter: load_workloads()
    Presenter->>Controller: Parallel fetch operations

    par Workload Sources
        Controller->>Fetchers: PodFetcher.fetch()
        Fetchers-->>Presenter: WorkloadsSourceLoaded("pods")
        Presenter->>UI: Partial table update
    and
        Controller->>Fetchers: NodeFetcher.fetch()
        Fetchers-->>Presenter: WorkloadsSourceLoaded("nodes")
    and
        Controller->>Controller: analyze PDBs
        Controller-->>Presenter: WorkloadsSourceLoaded("pdbs")
    and
        Controller->>Fetchers: TopMetricsFetcher.fetch()
        Fetchers-->>Presenter: WorkloadsSourceLoaded("metrics")
    end

    Presenter->>Presenter: Aggregate all sources
    Presenter->>Screen: WorkloadsDataLoaded
    Screen->>UI: Populate all tabs (All, Extreme, Single Replica, Missing PDB, Node Analysis)
```

## Reactive Data Updates

### Reactive Attribute Pattern

```python
class ClusterScreen(BaseScreen):
    """Screen with reactive data updates."""

    # Reactive attributes trigger watch methods when changed
    is_loading = reactive(False)
    data = reactive[dict]({})
    error = reactive[str | None](None)

    def watch_is_loading(self, loading: bool) -> None:
        """Update UI loading state."""
        loading_widget = self.query_one("#loading-indicator")
        loading_widget.display = loading

    def watch_data(self, data: dict) -> None:
        """Update tables and summaries when data changes."""
        if not data:
            return

        # Update nodes table
        nodes_table = self.query_one("#nodes-table", CustomDataTable)
        nodes_table.clear()
        for node in data.get("nodes", []):
            nodes_table.add_row(
                node.name,
                node.status.value,
                node.instance_type,
                f"{node.cpu_req_pct:.1f}%",
            )

    def watch_error(self, error: str | None) -> None:
        """Display error message."""
        if error:
            self.app.notify(error, severity="error")
```

### Watch Method Execution Order

```mermaid
sequenceDiagram
    participant Code
    participant Textual
    participant Validator
    participant Watch as watch_data()
    participant UI

    Code->>Textual: self.data = new_data
    Textual->>Validator: validate_data(new_data)
    Validator-->>Textual: validated
    Textual->>Watch: watch_data(new_data)
    Watch->>UI: Schedule widget refresh
```

## Data Caching

### AppState Cache

```python
# models/state/app_state.py
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
```

Note: `AppState` is a plain class (not a Pydantic `BaseModel`). Caching is coordinated through the `CacheManager` singleton in `utils/cache_manager.py`, not through `AppState` directly.

### Using Cached Data

Cache coordination is handled through `CacheManager` (in `utils/cache_manager.py`) and `AppState`:

```python
from kubeagle.utils.cache_manager import cache_manager

class ChartsExplorerScreen(BaseScreen):
    """Charts explorer screen with cache support."""

    async def _load_data(self) -> None:
        """Load data, using AppState cache if available."""
        state = self.app.state

        # Check if data is already available in state
        if state.charts:
            self.data = {"charts": state.charts}
            return

        # Fetch fresh data
        controller = ChartsController(charts_path=self.app.settings.charts_path)
        charts = await controller.analyze_all_charts_async()

        # Update state cache
        state.charts = charts
        self.data = {"charts": charts}
```

The `ScreenDataLoader` mixin provides built-in cache coordination via `CacheManager`:
```python
# In ScreenDataLoader._load_worker():
if force_refresh and self._cache_key:
    await cache_manager.invalidate(self._cache_key)
```

## Data Transformation Pipeline

### Chart Analysis Flow

```mermaid
graph TB
    YAML["Raw YAML Files"] --> Parse["ChartsController.analyze_all_charts_async()"]
    Parse --> Extract["Parse values.yaml<br/>Extract resource requests/limits<br/>Check probes, PDB, affinity"]
    Extract --> ChartInfo["list[ChartInfo]"]
    ChartInfo --> TableBuilder["ChartsTableBuilder.build_rows()"]
    TableBuilder --> Format["Format CPU/memory values<br/>Calculate ratios<br/>Apply status indicators"]
    Format --> DataTable["CustomDataTable.add_row()"]
    DataTable --> Rendered["Rendered Table in UI"]
```

### Cluster Health Flow

```mermaid
graph TB
    kubectl["kubectl get nodes/events/pdbs"] --> Controller["ClusterController"]
    Controller --> FetchNodes["fetch_nodes() -> list[NodeInfo]"]
    Controller --> FetchEvents["get_event_summary() -> EventSummary"]
    Controller --> FetchPDBs["fetch_pdbs() -> list[PDBInfo]"]
    Controller --> AnalyzePDBs["analyze_blocking_pdbs() -> dict"]

    FetchNodes --> ScreenData["ClusterScreen.data"]
    FetchEvents --> ScreenData
    FetchPDBs --> ScreenData
    AnalyzePDBs --> ScreenData

    ScreenData --> Tab1["Tab 1: Nodes - NodeTable"]
    ScreenData --> Tab2["Tab 2: Workloads"]
    ScreenData --> Tab3["Tab 3: Events - EventsTable"]
```

### Full Screen Data Flow Summary

```mermaid
graph LR
    subgraph "Per-Screen Data Sources"
        CS["ClusterScreen"] -.-> CC["ClusterController"]
        CES["ChartsExplorerScreen"] -.-> ChC["ChartsController"]
        CES -.-> TC["Team Module"]
        WS["WorkloadsScreen"] -.-> CC
        OS["OptimizerScreen"] -.-> OM["Optimizer Module"]
        OS -.-> ChC
        CDS["ChartDetailScreen"] -.-> ChC
        RES["ReportExportScreen"] -.-> AppState
        SS["SettingsScreen"] -.-> ConfigManager
    end
```

## Cluster Summary Utility Flow

The `utils/cluster_summary.py` module provides shared summary computation used by both the Home (Cluster) screen and other screens that display cluster health:

```mermaid
graph TB
    subgraph Input
        Nodes["list[NodeInfo]"]
        PDBs["list[PDBInfo]"]
        AllocatedData["allocated_data dict"]
    end

    subgraph ClusterSummary["utils/cluster_summary.py"]
        SummarizeNodes["summarize_nodes()<br/>-> node_count, ready_count,<br/>not_ready_count, cordoned_count,<br/>az_count, instance_type_count"]
        CountBlocking["count_blocking_pdbs()<br/>-> blocking_count"]
        CountGroups["count_node_groups()<br/>-> node_group_count"]
    end

    subgraph Consumers
        ClusterScreen["ClusterScreen"]
        HomeTab["Home / Summary Tab"]
    end

    Nodes --> SummarizeNodes
    PDBs --> CountBlocking
    AllocatedData --> CountGroups

    SummarizeNodes --> ClusterScreen
    SummarizeNodes --> HomeTab
    CountBlocking --> ClusterScreen
    CountGroups --> ClusterScreen
```

## Error Handling Flow

```python
@work(exclusive=True)
async def _load_data(self) -> None:
    """Data loading with error handling."""
    try:
        self.is_loading = True
        self.error = None

        result = await self.controller.fetch_data()

        # Validate result
        if not result:
            raise DataError("No data returned")

        self.data = result

    except ConnectionError as e:
        self.error = f"Connection failed: {e}"
        self.app.notify(
            "Failed to connect to cluster. Check your kubeconfig.",
            severity="error",
            timeout=10,
        )

    except TimeoutError:
        self.error = "Request timed out"
        self.app.notify(
            "Cluster request timed out. Retry or check cluster health.",
            severity="warning",
        )

    except Exception as e:
        self.error = str(e)
        logger.exception(f"Unexpected error: {e}")

    finally:
        self.is_loading = False
```

## Cross-References

- [Architecture Overview](overview.md) - Component relationships
- [Design Patterns](design-patterns.md) - Worker and reactive patterns
- [Controller Reference](../controllers/controller-reference.md) - Controller details
- [Model Reference](../models/model-reference.md) - Data model details
