"""Pytest configuration and fixtures for TUI tests."""

from __future__ import annotations

import pytest

from kubeagle.app import EKSHelmReporterApp


@pytest.fixture
def app() -> EKSHelmReporterApp:
    """Create an EKSHelmReporterApp instance for testing.

    This fixture provides a fresh app instance for each test.
    The app is configured with minimal settings to avoid external dependencies.
    """
    return EKSHelmReporterApp(skip_eks=True)
