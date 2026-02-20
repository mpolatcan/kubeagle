"""Chart Detail Screen - Detailed chart analysis view."""

import logging
from contextlib import suppress

from rich.markup import escape
from textual.app import ComposeResult
from textual.message import Message

from kubeagle.keyboard import CHART_DETAIL_SCREEN_BINDINGS
from kubeagle.models.charts.chart_info import ChartInfo
from kubeagle.screens.base_screen import BaseScreen
from kubeagle.screens.detail.config import (
    LABEL_ANTIAFFINITY,
    LABEL_CPU_LIM,
    LABEL_CPU_RATIO,
    LABEL_CPU_REQ,
    LABEL_HPA,
    LABEL_LIVENESS,
    LABEL_MEM_LIM,
    LABEL_MEM_RATIO,
    LABEL_MEM_REQ,
    LABEL_PDB,
    LABEL_PDB_MAX,
    LABEL_PDB_MIN,
    LABEL_PDB_TEMPLATE,
    LABEL_PRIORITY,
    LABEL_QOS,
    LABEL_READINESS,
    LABEL_REPLICAS,
    LABEL_STARTUP,
    LABEL_TEAM,
    LABEL_TOPOLOGY,
    LABEL_VALUES_FILE,
    QOS_COLORS,
    RATIO_GOOD_MAX,
    RATIO_WARN_MAX,
    SECTION_AVAILABILITY,
    SECTION_CONFIGURATION,
    SECTION_PROBES,
    SECTION_RESOURCES,
)
from kubeagle.screens.mixins.worker_mixin import WorkerMixin
from kubeagle.widgets import (
    CustomContainer,
    CustomFooter,
    CustomHeader,
    CustomLoadingIndicator,
    CustomStatic,
    CustomVertical,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Worker Messages for Cross-thread Communication
# ============================================================================


class ChartDetailDataLoaded(Message):
    """Message indicating chart detail data has been loaded."""

    def __init__(self, chart: ChartInfo) -> None:
        super().__init__()
        self.chart = chart


class ChartDetailDataLoadFailed(Message):
    """Message indicating chart detail data loading failed."""

    def __init__(self, error: str) -> None:
        super().__init__()
        self.error = error


class ChartDetailScreen(WorkerMixin, BaseScreen):
    """Detailed chart analysis view."""

    BINDINGS = CHART_DETAIL_SCREEN_BINDINGS
    CSS_PATH = "../../css/screens/chart_detail_screen.tcss"
    _LABEL_WIDTH = 18
    _MAX_VALUES_FILE_LENGTH = 72

    def __init__(
        self,
        chart: ChartInfo,
        chart_list: list[ChartInfo] | None = None,
        chart_index: int = 0,
    ):
        super().__init__()
        self.chart_name = chart.name
        self.chart_data: ChartInfo | None = chart
        self.chart_list: list[ChartInfo] = chart_list or []
        self.chart_index: int = chart_index

    @property
    def screen_title(self) -> str:
        if self.chart_list:
            return f"{self.chart_name} ({self.chart_index + 1}/{len(self.chart_list)})"
        return self.chart_name

    @staticmethod
    def _format_resource(value: float, unit: str) -> str:
        """Format a resource value, stripping unnecessary decimal places."""
        if value == int(value):
            return f"{int(value)}{unit}"
        return f"{value}{unit}"

    @classmethod
    def _format_line(cls, label: str, value: str) -> str:
        """Format aligned key-value text lines for detail sections."""
        return f"{label:<{cls._LABEL_WIDTH}} {value}"

    @classmethod
    def _shorten_values_file(cls, value: str) -> str:
        """Shorten a long values file path while preserving the tail."""
        if len(value) <= cls._MAX_VALUES_FILE_LENGTH:
            return value
        tail = value[-(cls._MAX_VALUES_FILE_LENGTH - 3):]
        return f"...{tail}"

    @staticmethod
    def _format_ratio(limit: float, request: float) -> str:
        """Format limit/request ratio with color coding and warning indicator."""
        if not request:
            return "N/A"
        ratio = limit / request
        ratio_str = f"{ratio:.1f}x"
        if ratio <= RATIO_GOOD_MAX:
            return f"[#30d158]{ratio_str}[/#30d158]"
        if ratio <= RATIO_WARN_MAX:
            return f"[#ff9f0a]{ratio_str}[/#ff9f0a]"
        return f"[bold #ff3b30]{ratio_str}[/bold #ff3b30]"

    def compose(self) -> ComposeResult:
        yield CustomHeader()
        yield CustomContainer(
            CustomVertical(
                CustomLoadingIndicator(classes="loading", id="loading-indicator"),
                CustomStatic("Loading chart data...", classes="loading", id="loading-message"),
                id="loading-row",
            ),
            id="loading-overlay",
        )
        yield CustomVertical(
            CustomStatic(
                f"Chart: {self.chart_name}"
                + (f"  [{self.chart_index + 1}/{len(self.chart_list)}]" if self.chart_list else ""),
                classes="chart-title",
                id="chart-title",
            ),
            CustomStatic(
                "Status: [#30d158]OK[/#30d158] good | [#ff9f0a]WARNING[/#ff9f0a] attention | [bold #ff3b30]ERROR[/bold #ff3b30] critical",
                id="status-legend",
            ),
            CustomContainer(
                CustomVertical(
                    CustomStatic(SECTION_RESOURCES, classes="section-header"),
                    CustomStatic("", id="res-cpu-req"),
                    CustomStatic("", id="res-cpu-lim"),
                    CustomStatic("", id="res-cpu-ratio"),
                    CustomStatic("", id="res-mem-req"),
                    CustomStatic("", id="res-mem-lim"),
                    CustomStatic("", id="res-mem-ratio"),
                    CustomStatic("", id="res-qos"),
                    classes="section-container",
                    id="resources-section",
                ),
                CustomVertical(
                    CustomStatic(SECTION_PROBES, classes="section-header"),
                    CustomStatic("", id="probe-liveness"),
                    CustomStatic("", id="probe-readiness"),
                    CustomStatic("", id="probe-startup"),
                    classes="section-container",
                    id="probes-section",
                ),
                CustomVertical(
                    CustomStatic(SECTION_AVAILABILITY, classes="section-header"),
                    CustomStatic("", id="avail-replicas"),
                    CustomStatic("", id="avail-pdb"),
                    CustomStatic("", id="avail-pdb-template"),
                    CustomStatic("", id="avail-pdb-min"),
                    CustomStatic("", id="avail-pdb-max"),
                    CustomStatic("", id="avail-hpa"),
                    CustomStatic("", id="avail-antiaffinity"),
                    CustomStatic("", id="avail-topology"),
                    classes="section-container",
                    id="availability-section",
                ),
                CustomVertical(
                    CustomStatic(SECTION_CONFIGURATION, classes="section-header"),
                    CustomStatic("", id="conf-team"),
                    CustomStatic("", id="conf-priority"),
                    CustomStatic("", id="conf-values"),
                    classes="section-container",
                    id="configuration-section",
                ),
                id="detail-grid",
            ),
            id="detail-content",
        )

        yield CustomFooter()

    async def load_data(self) -> None:
        """Load chart detail data and update all sections."""
        if not self.chart_data:
            self._show_error("Chart data not provided")
            return
        self._render_all_sections()

    def on_mount(self) -> None:
        """Called when screen is mounted."""
        super().on_mount()

    def _start_load_worker(self) -> None:
        """Trigger data render (kept for backward compatibility)."""
        self._render_all_sections()

    def _render_all_sections(self) -> None:
        """Render all detail sections with current chart data."""
        self._update_resources_section()
        self._update_probes_section()
        self._update_availability_section()
        self._update_configuration_section()

    def on_chart_detail_data_loaded(self, event: ChartDetailDataLoaded) -> None:
        """Handle successful chart detail load."""
        self.chart_data = event.chart
        self.hide_loading_overlay()
        self._render_all_sections()

    def on_chart_detail_data_load_failed(self, event: ChartDetailDataLoadFailed) -> None:
        """Handle failed chart detail load."""
        self._show_error(event.error)

    def _show_error(self, message: str) -> None:
        """Show error message in the loading overlay."""
        self.show_loading_overlay(f"Error: {message}", is_error=True)

    def _update_resources_section(self) -> None:
        """Update resources section with chart data."""
        if not self.chart_data:
            return

        chart = self.chart_data

        cpu_req = self._format_resource(chart.cpu_request, "m")
        self.query_one("#res-cpu-req", CustomStatic).update(self._format_line(LABEL_CPU_REQ, cpu_req))

        cpu_lim = self._format_resource(chart.cpu_limit, "m")
        self.query_one("#res-cpu-lim", CustomStatic).update(self._format_line(LABEL_CPU_LIM, cpu_lim))

        cpu_ratio = self._format_ratio(chart.cpu_limit, chart.cpu_request)
        self.query_one("#res-cpu-ratio", CustomStatic).update(self._format_line(LABEL_CPU_RATIO, cpu_ratio))

        mem_req = self._format_resource(chart.memory_request, "Mi")
        self.query_one("#res-mem-req", CustomStatic).update(self._format_line(LABEL_MEM_REQ, mem_req))

        mem_lim = self._format_resource(chart.memory_limit, "Mi")
        self.query_one("#res-mem-lim", CustomStatic).update(self._format_line(LABEL_MEM_LIM, mem_lim))

        mem_ratio = self._format_ratio(chart.memory_limit, chart.memory_request)
        self.query_one("#res-mem-ratio", CustomStatic).update(self._format_line(LABEL_MEM_RATIO, mem_ratio))

        # FIX UX-DETAIL-004: Use Rich color names instead of CSS class names
        qos = chart.qos_class.value if chart.qos_class else "Unknown"
        qos_color = QOS_COLORS.get(qos, "")
        qos_markup = f"[{qos_color}]{qos}[/{qos_color}]" if qos_color else qos
        self.query_one("#res-qos", CustomStatic).update(self._format_line(LABEL_QOS, qos_markup))

    def _update_probes_section(self) -> None:
        """Update probes section with chart data."""
        if not self.chart_data:
            return

        chart = self.chart_data

        liveness_markup = (
            "[#30d158]Configured[/#30d158]"
            if chart.has_liveness
            else "[bold #ff3b30]Missing[/bold #ff3b30]"
        )
        self.query_one("#probe-liveness", CustomStatic).update(
            self._format_line(LABEL_LIVENESS, liveness_markup)
        )

        readiness_markup = (
            "[#30d158]Configured[/#30d158]"
            if chart.has_readiness
            else "[bold #ff3b30]Missing[/bold #ff3b30]"
        )
        self.query_one("#probe-readiness", CustomStatic).update(
            self._format_line(LABEL_READINESS, readiness_markup)
        )

        startup_markup = (
            "[#30d158]Configured[/#30d158]"
            if chart.has_startup
            else "[bold #ff3b30]Missing[/bold #ff3b30]"
        )
        self.query_one("#probe-startup", CustomStatic).update(
            self._format_line(LABEL_STARTUP, startup_markup)
        )

    def _update_availability_section(self) -> None:
        """Update availability section with chart data."""
        if not self.chart_data:
            return

        chart = self.chart_data

        replicas = str(chart.replicas) if chart.replicas is not None else "Not set"
        if chart.replicas == 1:
            replicas_markup = f"[#ff9f0a]{replicas} (single replica)[/#ff9f0a]"
        elif chart.replicas is not None and chart.replicas > 1:
            replicas_markup = f"[#30d158]{replicas}[/#30d158]"
        else:
            replicas_markup = f"[#ff9f0a]{replicas}[/#ff9f0a]"
        self.query_one("#avail-replicas", CustomStatic).update(
            self._format_line(LABEL_REPLICAS, replicas_markup)
        )

        # PDB status with conditional sub-fields
        if chart.pdb_enabled:
            pdb_markup = "[#30d158]Enabled[/#30d158]"
            pdb_template_note = "with template" if chart.pdb_template_exists else "no template"
            self.query_one("#avail-pdb", CustomStatic).update(
                self._format_line(LABEL_PDB, f"{pdb_markup} ({pdb_template_note})")
            )

            pdb_tpl_icon = (
                "[#30d158]✅ Yes[/#30d158]"
                if chart.pdb_template_exists
                else "[bold #ff3b30]❌ No[/bold #ff3b30]"
            )
            self.query_one("#avail-pdb-template", CustomStatic).update(
                self._format_line(LABEL_PDB_TEMPLATE, pdb_tpl_icon)
            )
            self.query_one("#avail-pdb-template", CustomStatic).display = True

            pdb_min = (
                str(chart.pdb_min_available)
                if chart.pdb_min_available is not None
                else "[#ff9f0a]Not set[/#ff9f0a]"
            )
            self.query_one("#avail-pdb-min", CustomStatic).update(
                self._format_line(LABEL_PDB_MIN, pdb_min)
            )
            self.query_one("#avail-pdb-min", CustomStatic).display = True

            pdb_max = (
                str(chart.pdb_max_unavailable)
                if chart.pdb_max_unavailable is not None
                else "[#ff9f0a]Not set[/#ff9f0a]"
            )
            self.query_one("#avail-pdb-max", CustomStatic).update(
                self._format_line(LABEL_PDB_MAX, pdb_max)
            )
            self.query_one("#avail-pdb-max", CustomStatic).display = True
        else:
            self.query_one("#avail-pdb", CustomStatic).update(
                self._format_line(LABEL_PDB, "[#ff9f0a]Disabled[/#ff9f0a]")
            )
            # Hide PDB sub-fields when disabled
            self.query_one("#avail-pdb-template", CustomStatic).display = False
            self.query_one("#avail-pdb-min", CustomStatic).display = False
            self.query_one("#avail-pdb-max", CustomStatic).display = False

        self.query_one("#avail-hpa", CustomStatic).update(
            self._format_line(LABEL_HPA, "Not tracked")
        )

        antiaffinity = (
            "[#30d158]Enabled[/#30d158]"
            if chart.has_anti_affinity
            else "[bold #ff3b30]Missing[/bold #ff3b30]"
        )
        self.query_one("#avail-antiaffinity", CustomStatic).update(
            self._format_line(LABEL_ANTIAFFINITY, antiaffinity)
        )

        topology = (
            "[#30d158]Enabled[/#30d158]"
            if chart.has_topology_spread
            else "[bold #ff3b30]Missing[/bold #ff3b30]"
        )
        self.query_one("#avail-topology", CustomStatic).update(
            self._format_line(LABEL_TOPOLOGY, topology)
        )

    def _update_configuration_section(self) -> None:
        """Update configuration section with chart data."""
        if not self.chart_data:
            return

        chart = self.chart_data

        team = chart.team if chart.team else "Unknown"
        self.query_one("#conf-team", CustomStatic).update(self._format_line(LABEL_TEAM, escape(team)))

        priority = chart.priority_class if chart.priority_class else "[#ff9f0a]Not set[/#ff9f0a]"
        self.query_one("#conf-priority", CustomStatic).update(
            self._format_line(LABEL_PRIORITY, str(priority))
        )

        if chart.values_file:
            values_path = self._shorten_values_file(chart.values_file)
            values = f"[bold]{escape(values_path)}[/bold]"
        else:
            values = "[#ff9f0a]Not found[/#ff9f0a]"
        self.query_one("#conf-values", CustomStatic).update(
            self._format_line(LABEL_VALUES_FILE, values)
        )

    def _navigate_to_chart(self, index: int) -> None:
        """Navigate to a chart at the given index by updating data in-place."""
        if not self.chart_list or index < 0 or index >= len(self.chart_list):
            return
        chart = self.chart_list[index]
        self.chart_index = index
        self.chart_name = chart.name
        self.chart_data = chart

        # Update title
        with suppress(AttributeError, LookupError):
            self.query_one("#chart-title", CustomStatic).update(
                f"Chart: {self.chart_name}"
                + (f"  [{self.chart_index + 1}/{len(self.chart_list)}]" if self.chart_list else "")
            )
        self.app.title = f"KubEagle - {self.chart_name}"

        # Refresh all sections in-place
        self._render_all_sections()

    def action_next_chart(self) -> None:
        """Navigate to the next chart in the list."""
        if not self.chart_list:
            self.notify("No chart list available for navigation", severity="information")
            return
        next_index = self.chart_index + 1
        if next_index >= len(self.chart_list):
            self.notify("Already at the last chart", severity="information")
            return
        self._navigate_to_chart(next_index)

    def action_prev_chart(self) -> None:
        """Navigate to the previous chart in the list."""
        if not self.chart_list:
            self.notify("No chart list available for navigation", severity="information")
            return
        prev_index = self.chart_index - 1
        if prev_index < 0:
            self.notify("Already at the first chart", severity="information")
            return
        self._navigate_to_chart(prev_index)

    def action_refresh(self) -> None:
        """Refresh chart data by re-syncing from the chart list."""
        # Re-sync from chart_list if available (in case parent updated data)
        if self.chart_list and 0 <= self.chart_index < len(self.chart_list):
            self.chart_data = self.chart_list[self.chart_index]
            self.chart_name = self.chart_data.name

        if not self.chart_data:
            self._show_error("No chart data available")
            return

        self._render_all_sections()
        self.notify("Chart detail refreshed", severity="information")

    def action_show_help(self) -> None:
        """Show help information about status indicators."""
        from kubeagle.widgets import CustomConfirmDialog

        help_dialog = CustomConfirmDialog(
            message="[bold]Status Indicators:[/bold]\n\n"
            "[#30d158]OK[/#30d158] - Healthy\n"
            "[#ff9f0a]WARNING[/#ff9f0a] - Needs attention\n"
            "[bold #ff3b30]ERROR[/bold #ff3b30] - Critical\n\n"
            "[bold]Navigation:[/bold]\n"
            "  N = Next chart  |  P = Previous chart\n"
            "  ESC = Back to charts list\n\n"
            "[bold]Actions:[/bold]\n"
            "  R = Refresh data  |  ? = This help\n\n"
            "[bold]Sections:[/bold] Resources, Probes, Availability, Configuration",
        )
        self.app.push_screen(help_dialog)


__all__ = ["ChartDetailScreen"]
