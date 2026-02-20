"""Unit tests for timeout constants in constants/timeouts.py.

Tests cover:
- All timeout values
- Correct types (float or str)
- Positive values for numeric timeouts
- Logical relationships between timeout magnitudes
"""

from __future__ import annotations

from kubeagle.constants.timeouts import (
    CLUSTER_CHECK_TIMEOUT,
    CLUSTER_REQUEST_TIMEOUT,
    DEFAULT_TIMEOUT,
    HELM_COMMAND_TIMEOUT,
    KUBECTL_COMMAND_TIMEOUT,
    LONG_TIMEOUT,
    NODE_FETCH_TIMEOUT,
    NODE_GROUPS_TIMEOUT,
    SHORT_TIMEOUT,
    STATUS_UPDATE_INTERVAL,
    VIOLATION_CHECK_TIMEOUT,
)

# =============================================================================
# API/Cluster timeouts (string format)
# =============================================================================


class TestClusterRequestTimeout:
    """Test CLUSTER_REQUEST_TIMEOUT constant."""

    def test_type(self) -> None:
        assert isinstance(CLUSTER_REQUEST_TIMEOUT, str)

    def test_value(self) -> None:
        assert CLUSTER_REQUEST_TIMEOUT == "30s"

    def test_ends_with_s(self) -> None:
        assert CLUSTER_REQUEST_TIMEOUT.endswith("s")


# =============================================================================
# General timeouts (float, seconds)
# =============================================================================


class TestGeneralTimeouts:
    """Test general timeout constants."""

    def test_default_timeout_type(self) -> None:
        assert isinstance(DEFAULT_TIMEOUT, float)

    def test_default_timeout_value(self) -> None:
        assert DEFAULT_TIMEOUT == 30.0

    def test_default_timeout_positive(self) -> None:
        assert DEFAULT_TIMEOUT > 0

    def test_long_timeout_type(self) -> None:
        assert isinstance(LONG_TIMEOUT, float)

    def test_long_timeout_value(self) -> None:
        assert LONG_TIMEOUT == 60.0

    def test_long_timeout_positive(self) -> None:
        assert LONG_TIMEOUT > 0

    def test_short_timeout_type(self) -> None:
        assert isinstance(SHORT_TIMEOUT, float)

    def test_short_timeout_value(self) -> None:
        assert SHORT_TIMEOUT == 10.0

    def test_short_timeout_positive(self) -> None:
        assert SHORT_TIMEOUT > 0

    def test_short_less_than_default(self) -> None:
        assert SHORT_TIMEOUT < DEFAULT_TIMEOUT

    def test_default_less_than_long(self) -> None:
        assert DEFAULT_TIMEOUT < LONG_TIMEOUT


# =============================================================================
# Command-level process timeouts
# =============================================================================


class TestCommandTimeouts:
    """Test subprocess-level command timeout constants."""

    def test_kubectl_command_timeout_type(self) -> None:
        assert isinstance(KUBECTL_COMMAND_TIMEOUT, int)

    def test_kubectl_command_timeout_value(self) -> None:
        assert KUBECTL_COMMAND_TIMEOUT == 45

    def test_helm_command_timeout_type(self) -> None:
        assert isinstance(HELM_COMMAND_TIMEOUT, int)

    def test_helm_command_timeout_value(self) -> None:
        assert HELM_COMMAND_TIMEOUT == 30

# =============================================================================
# Async operation timeouts
# =============================================================================


class TestAsyncTimeouts:
    """Test async operation timeout constants."""

    def test_cluster_check_timeout_type(self) -> None:
        assert isinstance(CLUSTER_CHECK_TIMEOUT, float)

    def test_cluster_check_timeout_value(self) -> None:
        assert CLUSTER_CHECK_TIMEOUT == 12.0

    def test_cluster_check_timeout_positive(self) -> None:
        assert CLUSTER_CHECK_TIMEOUT > 0

    def test_node_fetch_timeout_type(self) -> None:
        assert isinstance(NODE_FETCH_TIMEOUT, float)

    def test_node_fetch_timeout_value(self) -> None:
        assert NODE_FETCH_TIMEOUT == 50.0

    def test_node_fetch_timeout_positive(self) -> None:
        assert NODE_FETCH_TIMEOUT > 0

    def test_node_groups_timeout_type(self) -> None:
        assert isinstance(NODE_GROUPS_TIMEOUT, float)

    def test_node_groups_timeout_value(self) -> None:
        assert NODE_GROUPS_TIMEOUT == 50.0

    def test_node_groups_timeout_positive(self) -> None:
        assert NODE_GROUPS_TIMEOUT > 0

    def test_violation_check_timeout_type(self) -> None:
        assert isinstance(VIOLATION_CHECK_TIMEOUT, float)

    def test_violation_check_timeout_value(self) -> None:
        assert VIOLATION_CHECK_TIMEOUT == 60.0

    def test_violation_check_timeout_positive(self) -> None:
        assert VIOLATION_CHECK_TIMEOUT > 0


# =============================================================================
# Refresh intervals
# =============================================================================


class TestRefreshIntervals:
    """Test refresh interval constants."""

    def test_status_update_interval_type(self) -> None:
        assert isinstance(STATUS_UPDATE_INTERVAL, float)

    def test_status_update_interval_value(self) -> None:
        assert STATUS_UPDATE_INTERVAL == 30.0

    def test_status_update_interval_positive(self) -> None:
        assert STATUS_UPDATE_INTERVAL > 0


# =============================================================================
# __all__ exports
# =============================================================================


class TestTimeoutsExports:
    """Test that __all__ exports are correct."""

    def test_all_exports_importable(self) -> None:
        import kubeagle.constants.timeouts as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"{name} listed in __all__ but not defined"
