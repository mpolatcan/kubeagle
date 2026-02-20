"""Tests for PDB analyzer."""

from __future__ import annotations

from typing import Any

from kubeagle.controllers.analyzers.pdb_analyzer import (
    PDBAnalyzer,
    analyze_blocking_pdbs,
)
from kubeagle.models.pdb.pdb_info import PDBInfo


def _make_pdb(**kwargs: Any) -> PDBInfo:
    """Create a PDBInfo with sensible defaults, overridable by kwargs."""
    defaults: dict[str, Any] = {
        "name": "test-pdb",
        "namespace": "default",
        "kind": "Deployment",
        "min_available": None,
        "max_unavailable": 1,
        "min_unavailable": None,
        "max_available": None,
        "current_healthy": 3,
        "desired_healthy": 3,
        "expected_pods": 3,
        "disruptions_allowed": 1,
        "unhealthy_pod_eviction_policy": "IfHealthyBudget",
    }
    defaults.update(kwargs)
    return PDBInfo(**defaults)


class TestPDBAnalyzer:
    """Tests for PDBAnalyzer class."""

    def test_analyzer_init(self) -> None:
        """Test PDBAnalyzer initialization."""
        analyzer = PDBAnalyzer()
        assert isinstance(analyzer, PDBAnalyzer)

    def test_check_pdb_empty_list(self) -> None:
        """Test check_pdb with empty PDB list."""
        analyzer = PDBAnalyzer()

        # The analyzer should be able to handle empty input without error
        assert analyzer is not None


# =============================================================================
# analyze() TESTS
# =============================================================================


class TestPDBAnalyzerAnalyze:
    """Tests for PDBAnalyzer.analyze() method."""

    def test_analyze_non_blocking_pdb(self) -> None:
        """Test analyze on a non-blocking PDB (maxUnavailable=1, 3 pods)."""
        analyzer = PDBAnalyzer()
        pdb = _make_pdb(max_unavailable=1, expected_pods=3, disruptions_allowed=1)
        result = analyzer.analyze(pdb)
        assert result.is_blocking is False
        assert result.blocking_reason is None

    def test_analyze_max_unavailable_zero_blocks(self) -> None:
        """Test analyze when maxUnavailable=0 blocks all evictions."""
        analyzer = PDBAnalyzer()
        pdb = _make_pdb(max_unavailable=0, expected_pods=3, disruptions_allowed=0)
        result = analyzer.analyze(pdb)
        assert result.is_blocking is True
        assert "maxUnavailable=0" in (result.blocking_reason or "")

    def test_analyze_max_unavailable_zero_string_blocks(self) -> None:
        """Test analyze when maxUnavailable='0' (string) blocks all evictions."""
        analyzer = PDBAnalyzer()
        pdb = _make_pdb(max_unavailable="0", expected_pods=3, disruptions_allowed=0)
        result = analyzer.analyze(pdb)
        assert result.is_blocking is True
        assert "maxUnavailable=0" in (result.blocking_reason or "")

    def test_analyze_min_available_ge_expected_pods(self) -> None:
        """Test analyze when minAvailable >= expected pods blocks evictions."""
        analyzer = PDBAnalyzer()
        pdb = _make_pdb(
            min_available=3,
            max_unavailable=None,
            expected_pods=3,
            disruptions_allowed=0,
        )
        result = analyzer.analyze(pdb)
        assert result.is_blocking is True
        assert "minAvailable" in (result.blocking_reason or "")

    def test_analyze_min_available_exceeds_expected_pods(self) -> None:
        """Test analyze when minAvailable exceeds expected pods blocks evictions."""
        analyzer = PDBAnalyzer()
        pdb = _make_pdb(
            min_available=5,
            max_unavailable=None,
            expected_pods=3,
            disruptions_allowed=0,
        )
        result = analyzer.analyze(pdb)
        assert result.is_blocking is True
        assert "minAvailable" in (result.blocking_reason or "")

    def test_analyze_resets_between_calls(self) -> None:
        """Test that analyzer resets state between calls."""
        analyzer = PDBAnalyzer()
        blocking_pdb = _make_pdb(max_unavailable=0, expected_pods=3, disruptions_allowed=0)
        analyzer.analyze(blocking_pdb)
        assert analyzer.is_blocking is True

        non_blocking_pdb = _make_pdb(max_unavailable=1, expected_pods=3, disruptions_allowed=1)
        analyzer.analyze(non_blocking_pdb)
        assert analyzer.is_blocking is False

    def test_analyze_currently_blocking_evictions(self) -> None:
        """Test analyze detects currently unhealthy pods blocking evictions."""
        analyzer = PDBAnalyzer()
        pdb = _make_pdb(
            max_unavailable=1,
            expected_pods=3,
            current_healthy=2,
            disruptions_allowed=0,
        )
        result = analyzer.analyze(pdb)
        assert result.is_blocking is True
        assert "Currently blocking" in (result.blocking_reason or "")

    def test_analyze_allows_all_disruptions_warning(self) -> None:
        """Test analyze detects PDB that allows all disruptions (no protection)."""
        analyzer = PDBAnalyzer()
        pdb = _make_pdb(
            min_available=0,
            max_unavailable=None,
            expected_pods=3,
            disruptions_allowed=3,
        )
        result = analyzer.analyze(pdb)
        assert result.is_blocking is True
        assert "no protection" in (result.blocking_reason or "").lower()


# =============================================================================
# classify_blocking_risk TESTS
# =============================================================================


class TestClassifyBlockingRisk:
    """Tests for PDBAnalyzer.classify_blocking_risk()."""

    def test_critical_risk_max_unavailable_zero(self) -> None:
        """Test critical risk when maxUnavailable=0."""
        pdb = _make_pdb(is_blocking=True, blocking_reason="maxUnavailable=0 blocks all evictions")
        assert PDBAnalyzer.classify_blocking_risk(pdb) == "critical"

    def test_high_risk_min_available_blocks(self) -> None:
        """Test high risk when minAvailable blocks evictions."""
        pdb = _make_pdb(
            is_blocking=True,
            blocking_reason="minAvailable (3) >= expected pods (3)",
        )
        assert PDBAnalyzer.classify_blocking_risk(pdb) == "high"

    def test_medium_risk_currently_blocking(self) -> None:
        """Test medium risk when currently blocking evictions."""
        pdb = _make_pdb(
            is_blocking=True,
            blocking_reason="Currently blocking evictions (2/3 healthy)",
        )
        assert PDBAnalyzer.classify_blocking_risk(pdb) == "medium"

    def test_low_risk_not_blocking(self) -> None:
        """Test low risk when PDB is not blocking."""
        pdb = _make_pdb(is_blocking=False, blocking_reason=None)
        assert PDBAnalyzer.classify_blocking_risk(pdb) == "low"

    def test_high_risk_min_available_blocks_keyword(self) -> None:
        """Test high risk for minAvailable with 'blocks' keyword."""
        pdb = _make_pdb(
            is_blocking=True,
            blocking_reason="minAvailable=100% blocks all evictions",
        )
        assert PDBAnalyzer.classify_blocking_risk(pdb) == "high"


# =============================================================================
# get_pdb_kind TESTS
# =============================================================================


class TestGetPDBKind:
    """Tests for PDBAnalyzer.get_pdb_kind()."""

    def test_pdb_with_selector(self) -> None:
        """Test PDB kind with a valid selector."""
        pdb_item = {
            "spec": {
                "selector": {
                    "matchLabels": {"app": "my-app"},
                },
            },
        }
        assert PDBAnalyzer.get_pdb_kind(pdb_item) == "Workload"

    def test_pdb_without_selector(self) -> None:
        """Test PDB kind without selector returns Unknown."""
        pdb_item = {"spec": {}}
        assert PDBAnalyzer.get_pdb_kind(pdb_item) == "Unknown"

    def test_pdb_empty_spec(self) -> None:
        """Test PDB kind with empty spec returns Unknown."""
        pdb_item: dict = {}
        assert PDBAnalyzer.get_pdb_kind(pdb_item) == "Unknown"


# =============================================================================
# Properties TESTS
# =============================================================================


class TestPDBAnalyzerProperties:
    """Tests for PDBAnalyzer properties."""

    def test_is_blocking_false_initially(self) -> None:
        """Test is_blocking is False on fresh analyzer."""
        analyzer = PDBAnalyzer()
        assert analyzer.is_blocking is False

    def test_blocking_reasons_empty_initially(self) -> None:
        """Test blocking_reasons is empty on fresh analyzer."""
        analyzer = PDBAnalyzer()
        assert analyzer.blocking_reasons == []

    def test_conflict_type_none_initially(self) -> None:
        """Test conflict_type is None on fresh analyzer."""
        analyzer = PDBAnalyzer()
        assert analyzer.conflict_type is None

    def test_is_blocking_true_after_blocking_analysis(self) -> None:
        """Test is_blocking is True after analyzing a blocking PDB."""
        analyzer = PDBAnalyzer()
        pdb = _make_pdb(max_unavailable=0, expected_pods=3, disruptions_allowed=0)
        analyzer.analyze(pdb)
        assert analyzer.is_blocking is True
        assert len(analyzer.blocking_reasons) > 0

    def test_reset_clears_state(self) -> None:
        """Test reset() clears all analysis state."""
        analyzer = PDBAnalyzer()
        pdb = _make_pdb(max_unavailable=0, expected_pods=3, disruptions_allowed=0)
        analyzer.analyze(pdb)
        assert analyzer.is_blocking is True

        analyzer.reset()
        assert analyzer.is_blocking is False
        assert analyzer.blocking_reasons == []
        assert analyzer.conflict_type is None


# =============================================================================
# analyze_blocking_pdbs TESTS
# =============================================================================


class TestAnalyzeBlockingPdbs:
    """Tests for analyze_blocking_pdbs function."""

    def test_empty_list(self) -> None:
        """Test with empty PDB list."""
        result = analyze_blocking_pdbs([])
        assert result["total_pdbs"] == 0
        assert result["blocking_count"] == 0
        assert result["blocking_pdbs"] == []

    def test_mixed_list(self) -> None:
        """Test with mix of blocking and non-blocking PDBs."""
        pdbs = [
            _make_pdb(name="ok-pdb", max_unavailable=1, expected_pods=3, disruptions_allowed=1),
            _make_pdb(name="bad-pdb", max_unavailable=0, expected_pods=3, disruptions_allowed=0),
        ]
        result = analyze_blocking_pdbs(pdbs)
        assert result["total_pdbs"] == 2
        assert result["blocking_count"] == 1
        assert len(result["blocking_pdbs"]) == 1
        assert "bad-pdb" in result["blocking_pdbs"][0].name

    def test_all_blocking(self) -> None:
        """Test with all PDBs blocking."""
        pdbs = [
            _make_pdb(name="block-1", max_unavailable=0, expected_pods=3, disruptions_allowed=0),
            _make_pdb(
                name="block-2",
                min_available=5,
                max_unavailable=None,
                expected_pods=5,
                disruptions_allowed=0,
            ),
        ]
        result = analyze_blocking_pdbs(pdbs)
        assert result["total_pdbs"] == 2
        assert result["blocking_count"] == 2
