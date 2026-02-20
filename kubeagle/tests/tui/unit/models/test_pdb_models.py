"""Tests for PDB models."""

from __future__ import annotations

from kubeagle.models.pdb.blocking_pdb import BlockingPDBInfo
from kubeagle.models.pdb.pdb_info import PDBInfo


class TestPDBInfo:
    """Tests for PDBInfo model."""

    def test_pdb_info_creation(self) -> None:
        """Test PDBInfo creation."""
        pdb = PDBInfo(
            name="my-pdb",
            namespace="default",
            kind="Workload",
            min_available=1,
            max_unavailable=None,
            min_unavailable=None,
            max_available=None,
            current_healthy=5,
            desired_healthy=5,
            expected_pods=5,
            disruptions_allowed=3,
            unhealthy_pod_eviction_policy="IfHealthyBudget",
        )

        assert pdb.name == "my-pdb"
        assert pdb.min_available == 1
        assert pdb.current_healthy == 5


class TestBlockingPDBInfo:
    """Tests for BlockingPDBInfo model."""

    def test_blocking_pdb_info_creation(self) -> None:
        """Test BlockingPDBInfo creation."""
        pdb = BlockingPDBInfo(
            name="blocking-pdb",
            namespace="default",
            min_available=3,
            max_unavailable=0,
            unhealthy_policy="IfHealthyBudget",
            expected_pods=3,
            disruptions_allowed=0,
            issues=["maxUnavailable=0 blocks all evictions"],
        )

        assert pdb.name == "blocking-pdb"
        assert pdb.max_unavailable == 0
        assert len(pdb.issues) == 1

    def test_blocking_pdb_info_with_multiple_issues(self) -> None:
        """Test BlockingPDBInfo with multiple issues."""
        pdb = BlockingPDBInfo(
            name="problem-pdb",
            namespace="default",
            min_available=1,
            max_unavailable=0,
            unhealthy_policy="IfHealthyBudget",
            expected_pods=3,
            disruptions_allowed=0,
            issues=[
                "maxUnavailable=0 blocks all evictions",
                "currentHealthy(2) < desiredHealthy(3)",
            ],
        )

        assert len(pdb.issues) == 2
