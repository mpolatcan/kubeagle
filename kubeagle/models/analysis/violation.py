"""Violation models."""

from pydantic import BaseModel, Field

from kubeagle.constants.enums import Severity


class ViolationResult(BaseModel):
    """Represents a violation result from optimization checks."""

    id: str
    chart_name: str
    chart_path: str | None = None
    team: str | None = None
    rule_name: str
    rule_id: str
    category: str  # resources, probes, availability, security
    severity: Severity
    description: str
    current_value: str
    recommended_value: str
    fix_available: bool
    analysis_source: str = "values"
    analysis_note: str = ""
    fix_verification_status: str = "not_run"
    fix_verification_note: str = ""
    wiring_suggestions: list[dict[str, str]] = Field(default_factory=list)
