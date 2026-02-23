"""Unit tests for fix verifier dataclasses."""

from __future__ import annotations

from kubeagle.optimizer import fix_verifier


def test_fix_verification_result_dataclass() -> None:
    """FixVerificationResult dataclass should be importable and constructible."""
    result = fix_verifier.FixVerificationResult(
        status="verified",
        note="test",
    )
    assert result.status == "verified"
    assert result.note == "test"
    assert result.before_has_violation is None
    assert result.after_has_violation is None
    assert result.suggestions == []


def test_full_fix_bundle_verification_result_dataclass() -> None:
    """FullFixBundleVerificationResult dataclass should be importable and constructible."""
    result = fix_verifier.FullFixBundleVerificationResult(
        status="not_run",
        note="skipped",
    )
    assert result.status == "not_run"
    assert result.per_violation == {}
