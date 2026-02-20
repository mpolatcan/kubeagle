"""CLI entry point for KubEagle TUI."""

from pathlib import Path
from typing import Annotated

import typer
from typer import Option

from kubeagle import __version__, run

app = typer.Typer(
    name="kubeagle",
    help="Interactive TUI for Kubernetes cluster exploration and Helm chart analysis",
)


@app.command()
def main(
    charts_path: Annotated[
        Path | None,
        Option(help="Path to Helm charts repository"),
    ] = None,
    skip_eks: Annotated[
        bool,
        Option(help="Skip EKS cluster analysis"),
    ] = False,
    context: Annotated[
        str | None,
        Option(help="AWS EKS context"),
    ] = None,
    active_charts: Annotated[
        Path | None,
        Option(help="Path to active charts file"),
    ] = None,
    from_cluster: Annotated[
        bool,
        Option(help="Fetch Helm values directly from cluster instead of local files"),
    ] = False,
    output_path: Annotated[
        Path | None,
        Option(help="Default path for report exports"),
    ] = None,
    version: Annotated[
        bool,
        Option(help="Show version information"),
    ] = False,
) -> None:
    """Run the KubEagle TUI application."""
    if version:
        typer.echo(f"KubEagle TUI v{__version__}")
        raise typer.Exit(0)
    run(
        charts_path=charts_path,
        skip_eks=skip_eks,
        context=context,
        active_charts_path=active_charts,
        from_cluster=from_cluster,
        output_path=output_path,
    )


if __name__ == "__main__":
    app()
