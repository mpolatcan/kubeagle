"""PDB analysis utilities for EKS cluster data operations."""

from __future__ import annotations

import logging
from typing import Any

from kubeagle.models.pdb.blocking_pdb import BlockingPDBInfo
from kubeagle.models.pdb.pdb_info import PDBInfo

logger = logging.getLogger(__name__)


class PDBAnalyzer:
    """Analyzes PodDisruptionBudgets for blocking issues and conflicts."""

    def __init__(self) -> None:
        self._blocking_reasons: list[str] = []
        self._conflict_type: str | None = None

    @property
    def blocking_reasons(self) -> list[str]:
        """Get list of blocking reasons found during analysis."""
        return self._blocking_reasons

    @property
    def conflict_type(self) -> str | None:
        """Get the type of conflict if found."""
        return self._conflict_type

    @property
    def is_blocking(self) -> bool:
        """Check if PDB is blocking operations."""
        return len(self._blocking_reasons) > 0 or self._conflict_type is not None

    def reset(self) -> None:
        """Reset analysis state."""
        self._blocking_reasons = []
        self._conflict_type = None

    def analyze(self, pdb: PDBInfo) -> PDBInfo:
        """Analyze a PDB for blocking issues and conflicts."""
        self.reset()
        self._check_conflicts(pdb)
        self._check_blocking_conditions(pdb)
        self._check_eviction_health(pdb)
        self._check_protection_level(pdb)

        pdb.is_blocking = self.is_blocking
        pdb.conflict_type = self._conflict_type
        pdb.blocking_reason = "; ".join(self._blocking_reasons) if self._blocking_reasons else None

        return pdb

    def _check_conflicts(self, pdb: PDBInfo) -> None:
        """Check for conflicting PDB configurations."""
        has_max_unavailable_val = pdb.max_unavailable is not None
        has_max_unavailable_percent = (
            isinstance(pdb.max_unavailable, str)
            and "%" in str(pdb.max_unavailable)
        )

        has_max_available_val = pdb.max_available is not None
        has_max_available_percent = (
            isinstance(pdb.max_available, str) and "%" in str(pdb.max_available)
        )

        has_min_unavailable = pdb.min_unavailable is not None
        has_max_available = pdb.max_available is not None or has_max_available_percent

        if has_max_unavailable_val and has_max_unavailable_percent:
            self._conflict_type = "maxUnavailable_conflict"
            self._blocking_reasons.append(
                "maxUnavailable and maxUnavailable% cannot both be set"
            )

        if has_max_available_val and has_max_available_percent:
            self._conflict_type = "maxAvailable_conflict"
            self._blocking_reasons.append(
                "maxAvailable and maxAvailable% cannot both be set"
            )

        if has_min_unavailable and has_max_available:
            self._conflict_type = "minUnavailable_maxAvailable_conflict"
            self._blocking_reasons.append(
                "minUnavailable and maxAvailable cannot both be set"
            )

    def _check_blocking_conditions(self, pdb: PDBInfo) -> None:
        """Check for conditions that block cluster operations."""
        expected_pods = pdb.expected_pods or 0

        if pdb.max_unavailable in (0, "0"):
            self._blocking_reasons.append("maxUnavailable=0 blocks all evictions")
            return

        if isinstance(pdb.max_unavailable, str) and "%" in pdb.max_unavailable:
            try:
                pct = int(pdb.max_unavailable.rstrip("%"))
                if pct == 0:
                    self._blocking_reasons.append("maxUnavailable=0% blocks all evictions")
                    return
            except ValueError:
                pass

        if pdb.min_available is not None and expected_pods > 0:
            if isinstance(pdb.min_available, int):
                if pdb.min_available >= expected_pods:
                    self._blocking_reasons.append(
                        f"minAvailable ({pdb.min_available}) >= expected pods ({expected_pods})"
                    )
            elif isinstance(pdb.min_available, str) and "%" in pdb.min_available:
                try:
                    pct = int(pdb.min_available.rstrip("%"))
                    if pct >= 100:
                        self._blocking_reasons.append(
                            f"minAvailable={pdb.min_available} blocks all evictions"
                        )
                    elif pct > 0:
                        effective_min = (expected_pods * pct + 99) // 100
                        if effective_min >= expected_pods:
                            self._blocking_reasons.append(
                                f"minAvailable={pdb.min_available} (effective: {effective_min}) >= expected pods ({expected_pods})"
                            )
                except ValueError:
                    pass

    def _check_eviction_health(self, pdb: PDBInfo) -> None:
        """Check if currently blocking evictions due to pod health."""
        expected_pods = pdb.expected_pods or 0
        disruptions_allowed = pdb.disruptions_allowed
        current_healthy = pdb.current_healthy

        if (
            disruptions_allowed == 0
            and expected_pods > 0
            and current_healthy < expected_pods
            and not self.is_blocking
        ):
            self._blocking_reasons.append(
                f"Currently blocking evictions ({current_healthy}/{expected_pods} healthy)"
            )

    def _check_protection_level(self, pdb: PDBInfo) -> None:
        """Check if PDB is too permissive (allows all disruptions)."""
        expected_pods = pdb.expected_pods or 0
        allows_all_disruptions = False

        if expected_pods > 0:
            if pdb.max_unavailable is not None:
                try:
                    max_unavail_val = int(pdb.max_unavailable)
                    if max_unavail_val >= expected_pods:
                        allows_all_disruptions = True
                except (ValueError, TypeError):
                    if (
                        isinstance(pdb.max_unavailable, str)
                        and "%" in pdb.max_unavailable
                    ):
                        try:
                            pct = int(pdb.max_unavailable.rstrip("%"))
                            if pct >= 100:
                                allows_all_disruptions = True
                        except ValueError:
                            pass

            if pdb.min_available == 0:
                allows_all_disruptions = True

            if allows_all_disruptions:
                self._blocking_reasons.append("Allows all disruptions - no protection")

    @staticmethod
    def get_pdb_kind(pdb_item: dict[str, Any]) -> str:
        """Determine the kind of workload the PDB protects."""
        spec = pdb_item.get("spec", {})
        selector = spec.get("selector", {})

        if not selector:
            return "Unknown"

        return "Workload"

    @staticmethod
    def classify_blocking_risk(pdb: PDBInfo) -> str:
        """Classify the risk level of a blocking PDB."""
        if not pdb.is_blocking or not pdb.blocking_reason:
            return "low"

        reasons_lower = pdb.blocking_reason.lower()

        if "maxunavailable=0" in reasons_lower:
            return "critical"
        elif "minavailable" in reasons_lower and ("blocks" in reasons_lower or ">=" in reasons_lower):
            return "high"
        elif "currently blocking" in reasons_lower:
            return "medium"
        else:
            return "high"


def analyze_blocking_pdbs(pdbs: list[PDBInfo]) -> dict[str, Any]:
    """Analyze PDBs that block cluster operations like node drains."""
    analyzer = PDBAnalyzer()
    blocking_pdbs: list[BlockingPDBInfo] = []

    for pdb in pdbs:
        analyzed_pdb = analyzer.analyze(pdb)
        if analyzed_pdb.is_blocking:
            risk_level = PDBAnalyzer.classify_blocking_risk(analyzed_pdb)
            blocking_pdbs.append(
                BlockingPDBInfo(
                    name=f"{analyzed_pdb.name} [{risk_level.upper()}]",
                    namespace=analyzed_pdb.namespace,
                    min_available=analyzed_pdb.min_available,
                    max_unavailable=analyzed_pdb.max_unavailable,
                    unhealthy_policy=analyzed_pdb.unhealthy_pod_eviction_policy,
                    expected_pods=analyzed_pdb.expected_pods,
                    disruptions_allowed=analyzed_pdb.disruptions_allowed,
                    issues=[analyzed_pdb.blocking_reason] if analyzed_pdb.blocking_reason else [],
                )
            )

    return {
        "total_pdbs": len(pdbs),
        "blocking_pdbs": blocking_pdbs,
        "blocking_count": len(blocking_pdbs),
    }


__all__ = ["PDBAnalyzer", "analyze_blocking_pdbs"]
