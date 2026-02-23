"""Regression tests for AI full-fix entry hydration in ViolationsView."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from kubeagle.constants.enums import Severity
from kubeagle.models.analysis.violation import ViolationResult
from kubeagle.optimizer.full_ai_fixer import AIFullFixResult
from kubeagle.optimizer.llm_patch_protocol import (
    FullFixResponse,
    FullFixTemplatePatch,
)
from kubeagle.screens.detail.components.ai_full_fix_bulk_modal import (
    AIFullFixBulkModal,
    AIFullFixBulkModalResult,
)
from kubeagle.screens.detail.components.violations_view import (
    ViolationsView,
    _MinimizedAIFixState,
)


@pytest.mark.unit
def test_notify_claude_agent_sdk_error_shows_error_toast(monkeypatch: pytest.MonkeyPatch) -> None:
    """Claude provider failures should show a toast with error details."""
    view = ViolationsView()
    captured: list[tuple[str, str]] = []

    def _capture_notify(message: str, *, severity: str = "information", **_: object) -> None:
        captured.append((message, severity))

    monkeypatch.setattr(view, "notify", _capture_notify)

    result = AIFullFixResult(
        ok=False,
        status="error",
        provider="claude",
        tried_providers=["claude"],
        errors=["claude: Agent SDK timed out after 120s"],
    )

    view._notify_claude_agent_sdk_error(result, context_label="AI full fix (demo)")

    assert captured
    message, severity = captured[0]
    assert severity == "error"
    assert "Claude Agent SDK error" in message
    assert "timed out" in message


@pytest.mark.unit
def test_notify_claude_agent_sdk_error_ignores_non_claude_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-Claude failures should not trigger Claude Agent SDK toast."""
    view = ViolationsView()
    captured: list[tuple[str, str]] = []

    def _capture_notify(message: str, *, severity: str = "information", **_: object) -> None:
        captured.append((message, severity))

    monkeypatch.setattr(view, "notify", _capture_notify)

    result = AIFullFixResult(
        ok=False,
        status="error",
        provider="codex",
        tried_providers=["codex"],
        errors=["codex: command timed out"],
    )

    view._notify_claude_agent_sdk_error(result, context_label="AI full fix (demo)")

    assert captured == []


@pytest.mark.unit
def test_notify_claude_agent_sdk_error_skips_successful_result_with_retry_warnings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Recovered Claude retry warnings should not raise error toasts when result is successful."""
    view = ViolationsView()
    captured: list[tuple[str, str]] = []

    def _capture_notify(message: str, *, severity: str = "information", **_: object) -> None:
        captured.append((message, severity))

    monkeypatch.setattr(view, "notify", _capture_notify)

    result = AIFullFixResult(
        ok=True,
        status="ok",
        provider="claude",
        tried_providers=["claude"],
        errors=["claude: Out-of-scope file edit detected: Chart.yaml"],
    )

    view._notify_claude_agent_sdk_error(result, context_label="AI full fix (demo)")

    assert captured == []


@pytest.mark.unit
def test_payload_can_apply_verified_subset_from_status_text() -> None:
    """Bulk payload should allow apply when verification has partial verified subset."""
    view = ViolationsView()
    payload = {
        "can_apply": "false",
        "status_text": (
            "Render Verification: UNRESOLVED\n"
            "Verification Details: Bundle verification: 3 verified, 3 unresolved, 0 unverified.\n"
        ),
    }

    assert view._payload_can_apply_verified_subset(payload) is True


@pytest.mark.unit
def test_bulk_chart_display_name_includes_values_file_type() -> None:
    """Bulk AI fix dialog should append values-file type to each chart label."""
    view = ViolationsView()
    chart = SimpleNamespace(
        chart_name="alchemy",
        values_file="/tmp/charts/alchemy/values-automation.yaml",
    )

    assert view._bulk_chart_display_name(chart) == "alchemy (Automation)"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_editor_bundle_allows_partial_verified_subset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Editor bundle should be apply-eligible without render verification."""
    view = ViolationsView()
    monkeypatch.setattr(
        view,
        "_local_chart_paths_from_chart",
        lambda _chart: (Path("/tmp/chart"), Path("/tmp/chart/values.yaml")),
    )
    monkeypatch.setattr(view, "_template_allowlist", lambda _chart_dir: set())

    can_apply, note, _values_patch, _template_patches, verification = await view._verify_editor_bundle(
        chart=object(),
        violations=[],
        values_patch_text="{}\n",
        template_diff_text="",
    )

    assert can_apply is True
    assert verification is None
    assert note == "Verification removed. Bundle is ready to apply."


@pytest.mark.unit
@pytest.mark.asyncio
async def test_entry_from_ai_result_uses_response_values_patch_when_no_direct_artifact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """JSON-contract responses should hydrate values editor payload instead of keeping {}."""
    view = ViolationsView()
    monkeypatch.setattr(
        view,
        "_provider_model_for_result",
        lambda _result: ("claude", "sonnet"),
    )
    monkeypatch.setattr(
        view,
        "_local_chart_paths_from_chart",
        lambda _chart: None,
    )

    violation = ViolationResult(
        id="v-1",
        chart_name="alchemy",
        rule_name="Replica Count",
        rule_id="AVL005",
        category="availability",
        severity=Severity.WARNING,
        description="replicaCount should be >= 2",
        current_value="1",
        recommended_value="2",
        fix_available=True,
    )
    response = FullFixResponse(
        result="ok",
        summary="Updated values and template wiring.",
        values_patch={"replicaCount": 2},
        template_patches=[
            FullFixTemplatePatch(
                file="templates/deployment.yaml",
                unified_diff=(
                    "--- a/templates/deployment.yaml\n"
                    "+++ b/templates/deployment.yaml\n"
                    "@@ -1 +1 @@\n"
                    "-old\n"
                    "+new\n"
                ),
            )
        ],
    )
    ai_result = AIFullFixResult(
        ok=True,
        status="ok",
        provider="claude",
        response=response,
        tried_providers=["claude"],
    )

    entry = await view._entry_from_ai_result(
        ai_result=ai_result,
        chart=object(),
        violations=[violation],
    )

    assert entry["values_patch_text"] == "replicaCount: 2\n"
    assert entry["values_preview_text"] == "replicaCount: 2\n"
    assert "+++ b/templates/deployment.yaml" in str(entry["template_preview_text"])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_bulk_raw_llm_action_falls_back_to_raw_output_when_execution_log_empty() -> None:
    """Raw output dialog should use raw_llm_output_text when execution_log_text is blank."""
    view = ViolationsView()
    captured: dict[str, str] = {}

    async def _capture_raw_llm(*, title: str, subtitle: str, raw_text: str, prompt_text: str = "") -> None:
        captured["title"] = title
        captured["subtitle"] = subtitle
        captured["raw_text"] = raw_text
        captured["prompt_text"] = prompt_text

    view._open_bulk_raw_llm_output_modal = _capture_raw_llm  # type: ignore[method-assign]

    chart = SimpleNamespace(chart_name="alchemy")
    grouped = {"chart-1": (chart, [])}
    result = cast(
        AIFullFixBulkModalResult,
        {
            "action": "raw-llm",
            "selected_chart_key": "chart-1",
            "bundles": {
                "chart-1": {
                    "execution_log_text": "",
                    "raw_llm_output_text": "provider raw payload",
                }
            },
        },
    )

    await view._handle_bulk_ai_full_fix_action(
        grouped,
        "Fix Selected Chart",
        result,
        modal=cast(AIFullFixBulkModal, SimpleNamespace()),
        keep_open=True,
    )

    assert captured["title"] == "LLM Output"
    assert captured["raw_text"] == "provider raw payload"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_bulk_reverify_preserves_timing_and_completion_lines() -> None:
    """Re-check should keep timing/completion metadata so status chips stay populated."""
    view = ViolationsView()

    class _DummyModal:
        def set_bundle_status(self, *, chart_key: str, status_text: str, can_apply: bool) -> None:
            _ = (chart_key, status_text, can_apply)

    view._status_with_provider_model = (  # type: ignore[method-assign]
        lambda message, **_kwargs: str(message)
    )

    chart = SimpleNamespace(chart_name="alchemy")
    grouped = {"chart-1": (chart, [])}
    payload = {
        "status_text": (
            "Provider: claude\n"
            "Model: haiku\n"
            "Timing: llm stage 31.8s\n"
            "Completion Time: 36.2s\n"
        ),
        "values_patch_text": "{}\n",
        "template_diff_text": "",
        "template_patches_json": "[]",
        "artifact_key": "",
    }
    result = cast(
        AIFullFixBulkModalResult,
        {
            "action": "reverify",
            "selected_chart_key": "chart-1",
            "bundles": {"chart-1": payload},
        },
    )

    await view._handle_bulk_ai_full_fix_action(
        grouped,
        "Fix Selected Chart",
        result,
        modal=cast(AIFullFixBulkModal, _DummyModal()),
        keep_open=True,
    )

    status_text = str(payload["status_text"])
    assert "Verification: REMOVED" in status_text
    assert "Details: Bundle is ready to apply." in status_text
    assert "Timing: llm stage 31.8s" in status_text
    assert "Completion Time: 36.2s" in status_text
    assert "Re-Verify:" not in status_text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_bulk_show_diff_action_falls_back_to_template_preview_text() -> None:
    """Show diff action should include template preview when template diff text is unavailable."""
    view = ViolationsView()
    captured: dict[str, str] = {}

    async def _capture_diff(
        *,
        title: str,
        subtitle: str,
        values_diff_text: str,
        template_diff_text: str,
    ) -> None:
        captured["title"] = title
        captured["subtitle"] = subtitle
        captured["values_diff_text"] = values_diff_text
        captured["template_diff_text"] = template_diff_text

    view._open_bulk_diff_view_modal = _capture_diff  # type: ignore[method-assign]

    chart = SimpleNamespace(chart_name="alchemy")
    grouped = {"chart-1": (chart, [])}
    result = cast(
        AIFullFixBulkModalResult,
        {
            "action": "show-diff",
            "selected_chart_key": "chart-1",
            "bundles": {
                "chart-1": {
                    "artifact_key": "",
                    "template_diff_text": "",
                    "template_preview_text": "# FILE: templates/deployment.yaml\nspec:\n  replicas: 2\n",
                }
            },
        },
    )

    await view._handle_bulk_ai_full_fix_action(
        grouped,
        "Fix Selected Chart",
        result,
        modal=cast(AIFullFixBulkModal, SimpleNamespace()),
        keep_open=True,
    )

    assert captured["title"] == "Bundle Diff"
    assert captured["values_diff_text"] == ""
    assert "# FILE: templates/deployment.yaml" in captured["template_diff_text"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_bulk_show_diff_refresh_updates_open_modal_bundle_state() -> None:
    """Show diff refresh should sync regenerated values/templates into the open bulk modal."""
    view = ViolationsView()
    chart = SimpleNamespace(chart_name="alchemy")
    grouped = {"chart-1": (chart, [])}

    class _DummyModal:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        def set_bundle_state(self, **kwargs: object) -> None:
            self.calls.append(dict(kwargs))

    modal = _DummyModal()
    view._get_ai_full_fix_artifact = lambda _artifact_key: object()  # type: ignore[method-assign]
    view._build_direct_edit_preview_texts = lambda **kwargs: (  # type: ignore[method-assign]
        "replicaCount: 2\n",
        "# FILE: templates/deployment.yaml\nspec:\n  replicas: 2\n",
        "--- a/values.yaml\n+++ b/values.yaml\n@@ -1 +1 @@\n-replicaCount: 1\n+replicaCount: 2\n",
        "replicaCount: 2\n",
        "--- a/templates/deployment.yaml\n+++ b/templates/deployment.yaml\n@@ -1 +1 @@\n-old\n+new\n",
    )

    async def _capture_diff(
        *,
        title: str,
        subtitle: str,
        values_diff_text: str,
        template_diff_text: str,
    ) -> None:
        _ = (title, subtitle, values_diff_text, template_diff_text)

    view._open_bulk_diff_view_modal = _capture_diff  # type: ignore[method-assign]

    result = cast(
        AIFullFixBulkModalResult,
        {
            "action": "show-diff",
            "selected_chart_key": "chart-1",
            "bundles": {
                "chart-1": {
                    "artifact_key": "artifact-1",
                    "status_text": "Render Verification: VERIFIED",
                    "can_apply": "true",
                    "values_patch_text": "{}\n",
                    "template_diff_text": "",
                    "template_preview_text": "",
                }
            },
        },
    )

    await view._handle_bulk_ai_full_fix_action(
        grouped,
        "Fix Selected Chart",
        result,
        modal=cast(AIFullFixBulkModal, modal),
        keep_open=True,
    )

    assert modal.calls
    last_call = modal.calls[-1]
    assert last_call["chart_key"] == "chart-1"
    assert last_call["values_patch_text"] == "replicaCount: 2\n"
    assert "# FILE: templates/deployment.yaml" in str(last_call["template_preview_text"])


def _sample_violation() -> ViolationResult:
    return ViolationResult(
        id="v-minimized",
        chart_name="alchemy",
        rule_name="Replica Count",
        rule_id="AVL005",
        category="availability",
        severity=Severity.WARNING,
        description="replicaCount should be >= 2",
        current_value="1",
        recommended_value="2",
        fix_available=True,
    )


@pytest.mark.unit
def test_minimized_single_banner_marks_timeout_status_as_finished() -> None:
    """Timeout cache entries should complete minimized single-progress banner."""
    view = ViolationsView()
    view._provider_signature = lambda: "test-provider"  # type: ignore[method-assign]
    violation = _sample_violation()
    chart = SimpleNamespace(chart_name="alchemy")
    grouped = {"chart-1": (chart, [violation])}
    run_id = "test-run-1"
    state = _MinimizedAIFixState(
        run_id=run_id,
        dialog_title="Fix Violation",
        grouped=grouped,
        total_count=1,
    )
    view._minimized_ai_fix_runs[run_id] = state
    cache_key = view._chart_bundle_ai_full_fix_cache_key(
        chart_key="chart-1",
        violations=[violation],
    )
    view._ai_full_fix_cache[cache_key] = {
        "status_text": "AI full-fix flow timed out. LLM stage exceeded time limit.",
        "can_apply": False,
    }

    view._refresh_minimized_runs()

    state = view._minimized_ai_fix_runs.get(run_id)
    assert state is not None
    assert state.completed_count == 1
    assert state.is_finished is True
    assert state.has_error is True
    assert state.status_text == "AI Fix complete for alchemy (Other): generation failed"


@pytest.mark.unit
def test_minimized_bulk_banner_counts_non_apply_terminal_status_as_complete() -> None:
    """Resolved cache statuses should complete bulk progress even when apply is unavailable."""
    view = ViolationsView()
    view._provider_signature = lambda: "test-provider"  # type: ignore[method-assign]
    violation = _sample_violation()
    chart = SimpleNamespace(chart_name="alchemy")
    grouped = {"chart-1": (chart, [violation])}
    run_id = "test-run-2"
    state = _MinimizedAIFixState(
        run_id=run_id,
        dialog_title="Fix All",
        grouped=grouped,
        total_count=1,
    )
    view._minimized_ai_fix_runs[run_id] = state
    cache_key = view._chart_bundle_ai_full_fix_cache_key(
        chart_key="chart-1",
        violations=[violation],
    )
    view._ai_full_fix_cache[cache_key] = {
        "status_text": (
            "Render Verification: UNRESOLVED\n"
            "Verification Details: Bundle verification: 0 verified, 2 unresolved, 2 unverified.\n"
        ),
        "can_apply": False,
    }

    view._refresh_minimized_runs()

    state = view._minimized_ai_fix_runs.get(run_id)
    assert state is not None
    assert state.completed_count == 1
    assert state.total_count == 1
    assert state.is_finished is True
    assert state.has_error is False
    assert state.status_text == "AI Fix complete for alchemy (Other)"
