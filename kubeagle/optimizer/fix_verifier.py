"""Fix verification dataclasses used by optimizer UI."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class FixVerificationResult:
    """Verification state for a single violation fix action."""

    status: str  # verified|unresolved|unverified|not_run
    note: str = ""
    before_has_violation: bool | None = None
    after_has_violation: bool | None = None
    suggestions: list[dict[str, str]] = field(default_factory=list)


@dataclass(slots=True)
class FullFixBundleVerificationResult:
    """Verification state for chart-level full fix bundle."""

    status: str  # verified|unresolved|unverified|not_run
    note: str = ""
    per_violation: dict[str, FixVerificationResult] = field(default_factory=dict)
