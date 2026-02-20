"""Unit tests for app startup-screen selection logic."""

from __future__ import annotations

from typing import Any

from kubeagle.app import EKSHelmReporterApp
from kubeagle.screens import ClusterScreen


def test_on_mount_defaults_to_cluster_screen() -> None:
    """App should mount ClusterScreen by default (phase 2 behavior)."""
    app = EKSHelmReporterApp(skip_eks=False)
    pushed: list[Any] = []

    app._activate_installed_screen = (  # type: ignore[method-assign]
        lambda _screen_name, screen_factory, **_kwargs: pushed.append(screen_factory())
    )
    app.call_after_refresh = lambda _callback: None  # type: ignore[method-assign]

    app.on_mount()

    assert pushed
    assert isinstance(pushed[0], ClusterScreen)


def test_on_mount_uses_cluster_screen_when_skip_eks_enabled() -> None:
    """App should mount ClusterScreen even when EKS analysis is skipped."""
    app = EKSHelmReporterApp(skip_eks=True)
    pushed: list[Any] = []

    app._activate_installed_screen = (  # type: ignore[method-assign]
        lambda _screen_name, screen_factory, **_kwargs: pushed.append(screen_factory())
    )
    app.call_after_refresh = lambda _callback: None  # type: ignore[method-assign]

    app.on_mount()

    assert pushed
    assert isinstance(pushed[0], ClusterScreen)
