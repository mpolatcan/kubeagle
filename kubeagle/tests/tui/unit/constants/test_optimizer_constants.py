"""Unit tests for optimizer threshold constants in constants/optimizer.py.

Tests cover:
- All optimizer threshold values
- Correct types
- Positive values
"""

from __future__ import annotations

from kubeagle.constants.optimizer import (
    LIMIT_REQUEST_RATIO_THRESHOLD,
    LOW_CPU_THRESHOLD_MILLICORES,
    LOW_MEMORY_THRESHOLD_MI,
    PDB_BLOCKING_THRESHOLD,
)

# =============================================================================
# Optimizer thresholds
# =============================================================================


class TestOptimizerThresholds:
    """Test optimizer threshold constants."""

    def test_limit_request_ratio_threshold_type(self) -> None:
        assert isinstance(LIMIT_REQUEST_RATIO_THRESHOLD, float)

    def test_limit_request_ratio_threshold_value(self) -> None:
        assert LIMIT_REQUEST_RATIO_THRESHOLD == 2.0

    def test_limit_request_ratio_threshold_positive(self) -> None:
        assert LIMIT_REQUEST_RATIO_THRESHOLD > 0

    def test_low_cpu_threshold_millicores_type(self) -> None:
        assert isinstance(LOW_CPU_THRESHOLD_MILLICORES, int)

    def test_low_cpu_threshold_millicores_value(self) -> None:
        assert LOW_CPU_THRESHOLD_MILLICORES == 10

    def test_low_cpu_threshold_millicores_positive(self) -> None:
        assert LOW_CPU_THRESHOLD_MILLICORES > 0

    def test_low_memory_threshold_mi_type(self) -> None:
        assert isinstance(LOW_MEMORY_THRESHOLD_MI, int)

    def test_low_memory_threshold_mi_value(self) -> None:
        assert LOW_MEMORY_THRESHOLD_MI == 32

    def test_low_memory_threshold_mi_positive(self) -> None:
        assert LOW_MEMORY_THRESHOLD_MI > 0

    def test_pdb_blocking_threshold_type(self) -> None:
        assert isinstance(PDB_BLOCKING_THRESHOLD, int)

    def test_pdb_blocking_threshold_value(self) -> None:
        assert PDB_BLOCKING_THRESHOLD == 1

    def test_pdb_blocking_threshold_positive(self) -> None:
        assert PDB_BLOCKING_THRESHOLD > 0


# =============================================================================
# __all__ exports
# =============================================================================


class TestOptimizerExports:
    """Test that __all__ exports are correct."""

    def test_all_exports_importable(self) -> None:
        import kubeagle.constants.optimizer as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"{name} listed in __all__ but not defined"
