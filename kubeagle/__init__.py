"""KubEagle TUI - Interactive terminal UI for Kubernetes cluster exploration."""

__version__ = "1.0.0"

from pathlib import Path


def run(
    charts_path: Path | None = None,
    skip_eks: bool = False,
    context: str | None = None,
    active_charts_path: Path | None = None,
    from_cluster: bool = False,
    output_path: Path | None = None,
) -> None:
    """Run the TUI application."""
    from kubeagle.app import EKSHelmReporterApp

    app = EKSHelmReporterApp(
        charts_path=charts_path,
        skip_eks=skip_eks,
        context=context,
        active_charts_path=active_charts_path,
        from_cluster=from_cluster,
        output_path=output_path,
    )
    app.run()
