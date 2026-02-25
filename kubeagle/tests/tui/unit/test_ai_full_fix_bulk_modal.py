"""Unit tests for AI full-fix bulk modal processing state behavior."""

from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest
from textual.app import App, ComposeResult

import kubeagle.screens.detail.components.ai_full_fix_modal as ai_full_fix_modal_module
from kubeagle.screens.detail.components.ai_full_fix_modal import (
    AIFullFixBulkModal,
    AIFullFixModal,
    ChartBundleEditorState,
    _CodePreview,
    _template_language_for_preview,
)


def _build_modal(*, can_apply: bool = False) -> AIFullFixBulkModal:
    bundle = ChartBundleEditorState(
        chart_key="chart-1",
        chart_name="alchemy",
        can_apply=can_apply,
    )
    return AIFullFixBulkModal(title="Fix Selected Chart", bundles=[bundle])


@pytest.mark.unit
def test_processing_status_detects_direct_edit_and_json_contract_messages() -> None:
    """Claude/Codex in-flight status lines should keep modal in processing mode."""
    assert AIFullFixBulkModal._is_processing_status("Trying direct-edit mode...")
    assert AIFullFixBulkModal._is_processing_status("Direct-edit: claude (attempt 1)...")
    assert AIFullFixBulkModal._is_processing_status("Trying JSON contract mode...")
    assert AIFullFixBulkModal._is_processing_status("Running codex (attempt 2)...")
    assert not AIFullFixBulkModal._is_processing_status("LLM: COMPLETED via claude")


@pytest.mark.unit
def test_processing_status_ignores_render_verification_pending() -> None:
    """Pending verification should not hide already-generated bundle results."""
    assert not AIFullFixBulkModal._is_processing_status("Render Verification: PENDING")


@pytest.mark.unit
def test_loading_label_normalizes_direct_edit_attempt_message() -> None:
    """Direct-edit attempt labels should be shown as a generic generation message."""
    assert (
        AIFullFixBulkModal._normalize_loading_message("Direct-edit: claude (attempt 1)...")
        == "Generating fix..."
    )
    assert (
        AIFullFixBulkModal._normalize_loading_message("Running codex (attempt 2)...")
        == "Generating fix..."
    )
    assert AIFullFixBulkModal._normalize_loading_message("Verifying...") == "Verifying..."


@pytest.mark.unit
def test_set_bundle_status_recomputes_processing_after_can_apply_toggle() -> None:
    """Regenerate status should switch bundle back to processing when can_apply becomes false."""
    modal = _build_modal(can_apply=True)
    modal._selected_chart_key = ""

    modal.set_bundle_status(
        chart_key="chart-1",
        status_text="Regenerating chart bundle...",
        can_apply=False,
    )

    bundle = modal._bundles["chart-1"]
    assert bundle.can_apply is False
    assert bundle.is_processing is True


@pytest.mark.unit
def test_apply_action_enabled_requires_verified_selected_bundle_and_no_loading() -> None:
    """Apply action should be enabled for completed selected bundle even while other jobs run."""
    modal = _build_modal(can_apply=True)
    modal._selected_chart_key = "chart-1"
    bundle = modal._bundles["chart-1"]

    bundle.is_processing = False
    bundle.is_waiting = False
    modal._active_loading_jobs = 0
    assert modal._apply_action_enabled() is True

    bundle.is_processing = True
    assert modal._apply_action_enabled() is False

    bundle.is_processing = False
    bundle.is_waiting = True
    assert modal._apply_action_enabled() is False

    bundle.is_waiting = False
    bundle.can_apply = False
    assert modal._apply_action_enabled() is False

    bundle.can_apply = True
    modal._active_loading_jobs = 1
    assert modal._apply_action_enabled() is True


@pytest.mark.unit
def test_action_buttons_locked_during_generation_except_close() -> None:
    """Bulk actions should lock based on selected chart, not unrelated global jobs."""
    modal = _build_modal(can_apply=True)
    bundle = modal._bundles["chart-1"]
    modal._selected_chart_key = "chart-1"

    assert modal._action_buttons_locked() is False

    modal._active_loading_jobs = 1
    assert modal._action_buttons_locked() is False

    modal._active_loading_jobs = 0
    bundle.is_processing = True
    assert modal._action_buttons_locked() is True

    bundle.is_processing = False
    bundle.is_waiting = True
    assert modal._action_buttons_locked() is True

    bundle.is_waiting = False
    modal._manual_action_lock = True
    assert modal._action_buttons_locked() is True

    modal._manual_action_lock = False
    assert modal._action_buttons_locked() is False


@pytest.mark.unit
def test_selected_loading_state_ignores_global_jobs_for_completed_bundle() -> None:
    """Completed selected bundle should stay visible even while other jobs run."""
    modal = _build_modal(can_apply=True)
    modal._selected_chart_key = "chart-1"
    bundle = modal._bundles["chart-1"]
    bundle.is_processing = False
    bundle.is_waiting = False
    modal._active_loading_jobs = 1

    assert modal._selected_bundle_loading_state() is False


@pytest.mark.unit
def test_selected_loading_state_forces_overlay_during_inline_regenerate() -> None:
    """Inline regenerate should re-show loading overlays even with existing preview content."""
    modal = _build_modal(can_apply=True)
    modal._selected_chart_key = "chart-1"
    bundle = modal._bundles["chart-1"]
    bundle.is_processing = False
    bundle.is_waiting = False
    bundle.values_preview_text = "replicaCount: 2\n"
    modal._manual_action_lock = True
    modal._active_loading_jobs = 1

    assert modal._selected_bundle_loading_state() is True


@pytest.mark.unit
def test_selected_loading_state_true_for_waiting_selected_bundle() -> None:
    """Queued selected bundle should keep loading overlay active."""
    modal = _build_modal(can_apply=False)
    modal._selected_chart_key = "chart-1"
    bundle = modal._bundles["chart-1"]
    bundle.is_waiting = True

    assert modal._selected_bundle_loading_state() is True


@pytest.mark.unit
def test_selected_loading_state_hides_overlay_when_processing_bundle_has_results() -> None:
    """Selected chart should keep showing existing results during in-flight refresh."""
    modal = _build_modal(can_apply=False)
    modal._selected_chart_key = "chart-1"
    bundle = modal._bundles["chart-1"]
    bundle.is_processing = True
    bundle.values_preview_text = "replicaCount: 2\n"

    assert modal._selected_bundle_loading_state() is False


@pytest.mark.unit
def test_buttons_remain_enabled_when_other_chart_processing() -> None:
    """Completed selected chart should keep actions available while a different chart runs."""
    modal = AIFullFixBulkModal(
        title="Fix All",
        bundles=[
            ChartBundleEditorState(
                chart_key="chart-1",
                chart_name="alpha",
                can_apply=True,
                is_processing=False,
                status_text="Render Verification: VERIFIED",
            ),
            ChartBundleEditorState(
                chart_key="chart-2",
                chart_name="beta",
                is_processing=True,
                status_text="Generating fix...",
            ),
        ],
    )
    modal._selected_chart_key = "chart-1"
    modal._active_loading_jobs = 1

    assert modal._action_buttons_locked() is False
    assert modal._apply_action_enabled() is True


@pytest.mark.unit
def test_apply_action_enabled_allows_partial_verified_subset() -> None:
    """Apply action should remain available when bundle has verified subset and zero unverified."""
    modal = _build_modal(can_apply=False)
    modal._selected_chart_key = ""
    bundle = modal._bundles["chart-1"]
    modal._active_loading_jobs = 0

    modal.set_bundle_status(
        chart_key="chart-1",
        status_text=(
            "Render Verification: UNRESOLVED\n"
            "Verification Details: Bundle verification: 3 verified, 3 unresolved, 0 unverified.\n"
        ),
        can_apply=False,
    )

    modal._selected_chart_key = "chart-1"
    assert bundle.can_apply is True
    assert modal._apply_action_enabled() is True
    assert modal._fix_status_label(bundle) == "Partial Fix"


@pytest.mark.unit
def test_single_modal_actions_locked_while_generating() -> None:
    """Single modal should lock actions while status indicates generation is running."""
    modal = AIFullFixModal(
        title="AI Full Fix",
        subtitle="demo",
        status_text="Generating fix...",
        can_apply=True,
    )
    assert modal._actions_locked() is True

    modal.set_status("Render Verification: VERIFIED", can_apply=True)
    assert modal._actions_locked() is False


@pytest.mark.unit
def test_single_modal_close_uses_minimize_when_button_label_is_minimize() -> None:
    """Close click should still minimize when the rendered button label says Minimize."""
    modal = AIFullFixModal(
        title="AI Full Fix",
        subtitle="demo",
        status_text="Render Verification: VERIFIED",
        can_apply=False,
    )
    dismissed: list[object] = []

    def _capture_dismiss(payload: object) -> None:
        dismissed.append(payload)

    modal.dismiss = _capture_dismiss  # type: ignore[method-assign]
    modal.query_one = lambda *_args, **_kwargs: SimpleNamespace(label="Minimize")  # type: ignore[method-assign]

    event = SimpleNamespace(button=SimpleNamespace(id="ai-full-fix-close"))
    modal.on_button_pressed(event)  # type: ignore[arg-type]

    assert dismissed == [ai_full_fix_modal_module.MODAL_MINIMIZED_SENTINEL]


@pytest.mark.unit
def test_chip_display_value_compacts_verification_details_counts() -> None:
    """Verification details chip should stay compact to avoid oversized card height."""
    compact = AIFullFixBulkModal._chip_display_value(
        "Verification Details",
        "Bundle verification: 4 verified, 1 unresolved, 0 unverified.",
    )
    assert compact == "4 verified | 1 unresolved | 0 unverified"


@pytest.mark.unit
def test_chip_tooltip_shows_full_verification_details_message() -> None:
    """Verification details chip should expose full text via hover tooltip."""
    tooltip = AIFullFixBulkModal._chip_tooltip(
        "Verification Details",
        "Bundle verification: 0 verified, 2 unresolved, 0 unverified. Render failed due to missing dependency chart.",
    )
    assert tooltip == (
        "Bundle verification: 0 verified, 2 unresolved, 0 unverified. "
        "Render failed due to missing dependency chart."
    )


@pytest.mark.unit
def test_chip_tooltip_ignored_for_non_verification_fields() -> None:
    """Only verification details should get hover tooltip payload."""
    tooltip = AIFullFixBulkModal._chip_tooltip("Status", "Incomplete Fix")
    assert tooltip is None


@pytest.mark.unit
def test_editor_text_falls_back_to_patch_or_diff_when_preview_is_empty() -> None:
    """Editor panes should not stay blank while preview payloads are still catching up."""
    bundle = ChartBundleEditorState(
        chart_key="chart-1",
        chart_name="alchemy",
        values_patch_text="replicaCount: 2\n",
        values_preview_text="{}\n",
        template_diff_text="--- a/templates/deployment.yaml\n+++ b/templates/deployment.yaml",
        template_preview_text="",
    )

    assert AIFullFixBulkModal._resolve_values_editor_text(bundle) == "replicaCount: 2\n"
    assert AIFullFixBulkModal._resolve_template_preview_text(bundle) == bundle.template_diff_text


@pytest.mark.unit
def test_template_preview_language_uses_markdown_for_tpl_files() -> None:
    """Helm template previews should avoid YAML lexer assumptions for .tpl files."""
    assert _template_language_for_preview("templates/_helpers.tpl", '{{ include "x" . }}') == "markdown"


@pytest.mark.unit
def test_template_preview_language_detects_unified_diff_when_no_yaml_extension() -> None:
    """Unified diff payloads should keep diff intent even when file name is synthetic."""
    diff_text = "--- a/templates/deployment.yaml\n+++ b/templates/deployment.yaml\n@@ -1 +1 @@\n-old\n+new\n"
    assert _template_language_for_preview("templates/preview-unavailable", diff_text) == "diff"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_code_preview_supports_vertical_scrolling_after_mount() -> None:
    """Read-only preview should expose vertical overflow for long payloads."""

    class _Harness(App[None]):
        CSS = """
        #preview {
            width: 64;
            height: 20;
            overflow-y: auto;
            overflow-x: auto;
        }
        """

        def compose(self) -> ComposeResult:
            long_text = "\n".join(f"line {index}" for index in range(1, 220))
            yield _CodePreview(text=long_text, id="preview")

    app = _Harness()
    async with app.run_test(size=(120, 40)) as pilot:
        preview = app.query_one("#preview", _CodePreview)
        await pilot.pause()
        assert preview.max_scroll_y > 0

        before = float(preview.scroll_y)
        preview.scroll_down(animate=False)
        await pilot.pause()

        assert float(preview.scroll_y) > before


@pytest.mark.unit
def test_code_preview_updates_language_theme_and_text() -> None:
    """Read-only preview should refresh code and retain theme/language compatibility."""
    preview = _CodePreview(text="line1\nline2\nline3\n")
    preview.set_code("a: 1\n", language="yaml", theme="monokai")

    assert preview.text == "a: 1\n"
    assert preview.language in set(preview.available_languages)
    assert preview.theme in set(preview.available_themes)


@pytest.mark.unit
def test_completion_time_label_sums_timing_tokens() -> None:
    """Completion time chip should use timing tokens when explicit completion line is missing."""
    modal = _build_modal()
    bundle = modal._bundles["chart-1"]
    bundle.status_text = (
        "Render Verification: UNRESOLVED\n"
        "Verification Details: pending\n"
        "Timing: llm stage 31.2s | preview stage 2.4s | verify stage 4.0s\n"
    )

    assert modal._completion_time_label(bundle) == "37.6s"


@pytest.mark.unit
def test_completion_time_label_uses_live_elapsed_while_processing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """In-flight bundles should show live elapsed duration instead of stale timing text."""
    modal = _build_modal()
    bundle = modal._bundles["chart-1"]
    bundle.status_text = "Timing: llm stage 31.2s"
    bundle.is_processing = True
    bundle.fix_started_at_monotonic = 100.0

    monkeypatch.setattr(ai_full_fix_modal_module.time, "monotonic", lambda: 104.25)

    assert modal._completion_time_label(bundle) == "4.2s"


@pytest.mark.unit
def test_completion_time_label_uses_recorded_elapsed_when_status_is_empty() -> None:
    """Completed bundles should keep the last measured elapsed value when status has no timing."""
    modal = _build_modal()
    bundle = modal._bundles["chart-1"]
    bundle.last_fix_elapsed_seconds = 6.4

    assert modal._completion_time_label(bundle) == "6.4s"


@pytest.mark.unit
def test_completion_time_label_shows_queued_for_waiting_bundle() -> None:
    """Queued bundles should display waiting state instead of elapsed time."""
    modal = _build_modal()
    bundle = modal._bundles["chart-1"]
    bundle.is_waiting = True
    bundle.status_text = "Queued: waiting for fix worker..."

    assert modal._completion_time_label(bundle) == "Queued"


@pytest.mark.unit
def test_tree_elapsed_label_uses_completion_time_and_skips_na() -> None:
    """Tree rows should include elapsed suffix only when a duration exists."""
    modal = _build_modal()
    bundle = modal._bundles["chart-1"]
    bundle.status_text = "Completion Time: 12.7s"
    assert modal._tree_elapsed_label(bundle) == " | 12.7s"

    bundle.status_text = "Render Verification: VERIFIED"
    bundle.last_fix_elapsed_seconds = None
    assert modal._tree_elapsed_label(bundle) == ""


@pytest.mark.unit
def test_tree_elapsed_label_skips_queued_waiting_state() -> None:
    """Tree rows should hide elapsed suffix while bundle is still queued."""
    modal = _build_modal()
    bundle = modal._bundles["chart-1"]
    bundle.is_waiting = True
    bundle.status_text = "Queued: waiting for fix worker..."

    assert modal._tree_elapsed_label(bundle) == ""
    assert modal._chart_marker(bundle) == "⏳"


@pytest.mark.unit
def test_chart_row_color_waiting_is_blue() -> None:
    """Queued charts should be blue in the left tree pane."""
    modal = _build_modal()
    bundle = modal._bundles["chart-1"]
    bundle.is_waiting = True
    bundle.status_text = "Queued: waiting for fix worker..."

    assert modal._chart_row_color(bundle) == "blue"


@pytest.mark.unit
def test_chart_row_color_running_is_yellow() -> None:
    """In-flight charts should be yellow in the left tree pane."""
    modal = _build_modal()
    bundle = modal._bundles["chart-1"]
    bundle.is_processing = True
    bundle.status_text = "Generating fix..."

    assert modal._chart_row_color(bundle) == "yellow"


@pytest.mark.unit
def test_chart_row_color_success_is_green() -> None:
    """Apply-ready charts should be green in the left tree pane."""
    modal = _build_modal(can_apply=True)
    bundle = modal._bundles["chart-1"]
    bundle.status_text = "Render Verification: VERIFIED"

    assert modal._chart_row_color(bundle) == "green"


@pytest.mark.unit
def test_chart_row_color_error_is_red() -> None:
    """Failed charts should be red in the left tree pane."""
    modal = _build_modal()
    bundle = modal._bundles["chart-1"]
    bundle.status_text = "AI full-fix flow failed: timeout"

    assert modal._chart_row_color(bundle) == "red"


@pytest.mark.unit
def test_fix_status_label_handles_legacy_reverify_key() -> None:
    """Legacy re-verify status lines should still map to complete fix label when verified."""
    modal = _build_modal()
    bundle = modal._bundles["chart-1"]
    bundle.status_text = "Re-Verify: VERIFIED\nVerification Details: ok"

    assert modal._fix_status_label(bundle) == "Complete Fix"


@pytest.mark.unit
def test_bulk_progress_counts_include_verified_and_completed_states() -> None:
    """Progress should count finished bundles, including verified subsets."""
    modal = AIFullFixBulkModal(
        title="Fix All",
        bundles=[
            ChartBundleEditorState(
                chart_key="chart-1",
                chart_name="alpha",
                is_processing=True,
                status_text="Generating fix...",
            ),
            ChartBundleEditorState(
                chart_key="chart-2",
                chart_name="beta",
                is_processing=False,
                can_apply=True,
                status_text="Render Verification: VERIFIED",
            ),
            ChartBundleEditorState(
                chart_key="chart-3",
                chart_name="gamma",
                is_processing=False,
                status_text="AI full-fix flow failed: timeout",
            ),
        ],
    )

    assert modal._bulk_progress_counts() == (2, 3)


@pytest.mark.unit
def test_bulk_elapsed_label_tracks_global_wall_time_from_first_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Elapsed label should track wall time from first started fix, not summed bundle durations."""
    modal = AIFullFixBulkModal(
        title="Fix All",
        bundles=[
            ChartBundleEditorState(
                chart_key="chart-1",
                chart_name="alpha",
                is_processing=True,
                fix_started_at_monotonic=100.0,
                status_text="Generating fix...",
            ),
            ChartBundleEditorState(
                chart_key="chart-2",
                chart_name="beta",
                is_processing=False,
                last_fix_elapsed_seconds=5.5,
                status_text="Render Verification: VERIFIED",
            ),
            ChartBundleEditorState(
                chart_key="chart-3",
                chart_name="gamma",
                is_waiting=True,
                is_processing=False,
                status_text="Queued: waiting for fix worker...",
            ),
        ],
    )

    monkeypatch.setattr(ai_full_fix_modal_module.time, "monotonic", lambda: 104.0)

    assert modal._bulk_total_elapsed_seconds() == pytest.approx(4.0)
    assert modal._bulk_elapsed_label() == "Elapsed 4.0s"


@pytest.mark.unit
def test_bulk_elapsed_label_waits_until_first_fix_start() -> None:
    """Global elapsed should stay in waiting state until a bundle actively starts."""
    modal = AIFullFixBulkModal(
        title="Fix All",
        bundles=[
            ChartBundleEditorState(
                chart_key="chart-1",
                chart_name="alpha",
                is_waiting=True,
                status_text="Queued: waiting for fix worker...",
            )
        ],
    )

    assert modal._bulk_total_elapsed_seconds() == pytest.approx(0.0)
    assert modal._bulk_elapsed_label() == "Waiting..."


@pytest.mark.unit
@pytest.mark.parametrize(
    ("button_id", "expected_action"),
    (
        ("ai-full-fix-bulk-show-diff", "show-diff"),
    ),
)
def test_diff_actions_run_inline_without_dismissing_modal(
    button_id: str,
    expected_action: str,
) -> None:
    """Show-diff action should stay inline so the bulk modal doesn't close/reopen."""
    modal = _build_modal()
    captured_inline: list[str] = []
    dismissed: list[object] = []

    async def _noop_handler(_payload: object) -> None:
        return None

    def _capture_inline(payload: object) -> None:
        if isinstance(payload, dict):
            payload_dict = cast(dict[str, object], payload)
            captured_inline.append(str(payload_dict.get("action", "")))

    def _capture_dismiss(payload: object) -> None:
        dismissed.append(payload)

    modal.set_inline_action_handler(_noop_handler)
    modal._run_inline_action = _capture_inline  # type: ignore[method-assign]
    modal.dismiss = _capture_dismiss  # type: ignore[method-assign]

    event = SimpleNamespace(button=SimpleNamespace(id=button_id))
    modal.on_button_pressed(event)  # type: ignore[arg-type]

    assert captured_inline == [expected_action]
    assert dismissed == []


@pytest.mark.unit
def test_bulk_close_uses_minimize_when_button_label_is_minimize() -> None:
    """Bulk close click should minimize when user-visible label is Minimize."""
    modal = _build_modal()
    modal._active_loading_jobs = 0
    modal._bundles["chart-1"].is_processing = False
    modal._bundles["chart-1"].is_waiting = False

    dismissed: list[object] = []

    def _capture_dismiss(payload: object) -> None:
        dismissed.append(payload)

    modal.dismiss = _capture_dismiss  # type: ignore[method-assign]
    modal.query_one = lambda *_args, **_kwargs: SimpleNamespace(label="Minimize")  # type: ignore[method-assign]

    event = SimpleNamespace(button=SimpleNamespace(id="ai-full-fix-bulk-close"))
    modal.on_button_pressed(event)  # type: ignore[arg-type]

    assert dismissed == [ai_full_fix_modal_module.MODAL_MINIMIZED_SENTINEL]
