"""Tests for type models."""

from __future__ import annotations

from kubeagle.models.types.columns import ColumnDef
from kubeagle.models.types.loading import (
    LoadingProgress,
    LoadResult,
)


class TestColumnDef:
    """Tests for ColumnDef model."""

    def test_column_def_creation(self) -> None:
        """Test ColumnDef creation."""
        column = ColumnDef(
            label="Name",
            key="name",
            numeric=False,
        )

        assert column.label == "Name"
        assert column.key == "name"
        assert column.numeric is False


class TestLoadingProgress:
    """Tests for LoadingProgress model."""

    def test_loading_progress_creation(self) -> None:
        """Test LoadingProgress creation."""
        progress = LoadingProgress(
            phase="loading",
            progress=0.5,
            message="Loading data...",
        )

        assert progress.phase == "loading"
        assert progress.progress == 0.5
        assert progress.message == "Loading data..."


class TestLoadResult:
    """Tests for LoadResult model."""

    def test_load_result_success(self) -> None:
        """Test LoadResult creation with success."""
        result = LoadResult(
            success=True,
            data={"key": "value"},
            duration_ms=100.0,
        )

        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None

    def test_load_result_error(self) -> None:
        """Test LoadResult creation with error."""
        result = LoadResult(
            success=False,
            error="Failed to load",
            duration_ms=50.0,
        )

        assert result.success is False
        assert result.data is None
        assert result.error == "Failed to load"
