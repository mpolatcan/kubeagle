"""Smoke tests for AI-only fix flow in ViolationsView."""

from __future__ import annotations

import inspect

import pytest

from kubeagle.screens.detail.components.ai_full_fix_bulk_modal import (
    AIFullFixBulkModal,
)
from kubeagle.screens.detail.components.ai_full_fix_modal import (
    AIFullFixModal,
)
from kubeagle.screens.detail.components.violations_view import (
    ViolationsView,
)


@pytest.mark.smoke
class TestViolationsAIFullFixFlow:
    """Validate AI-only full-fix wiring for single and bulk actions."""

    def test_fix_violation_opens_single_chart_bundled_modal(self) -> None:
        """Fix violation action should route to chart-bundled modal for one chart."""
        source = inspect.getsource(ViolationsView.fix_violation)
        assert "_open_ai_full_fix_bulk_modal" in source
        assert "Fix Selected Chart" in source
        assert "_open_apply_all_preview_modal" not in source

    def test_fix_all_selected_uses_chart_bundled_bulk_modal(self) -> None:
        """Fix Selected Chart should use chart-level bundled AI modal flow."""
        source = inspect.getsource(ViolationsView.fix_all_selected)
        assert "_open_ai_full_fix_bulk_modal" in source
        assert "Fix Selected Chart" in source

    def test_apply_all_uses_chart_bundled_bulk_modal(self) -> None:
        """Fix All should route through chart-bundled AI bulk modal."""
        source = inspect.getsource(ViolationsView.apply_all)
        assert "_open_ai_full_fix_bulk_modal" in source
        assert "Fix All" in source

    def test_preview_fix_and_double_click_use_ai_single_modal(self) -> None:
        """Preview paths should now route to AI full-fix modal instead of deterministic fix dialog."""
        preview_source = inspect.getsource(ViolationsView.preview_fix)
        show_source = inspect.getsource(ViolationsView._show_fix_preview)
        assert "_open_ai_full_fix_modal_for_single_violation" in preview_source
        assert "_open_ai_full_fix_modal_for_single_violation" in show_source
        assert "ai-wiring" not in show_source

    def test_bulk_modal_generation_groups_by_chart_and_uses_single_request_path(self) -> None:
        """Bulk flow should group violations by chart and generate chart bundle entries."""
        source = inspect.getsource(ViolationsView._open_ai_full_fix_bulk_modal)
        assert "_group_violations_by_chart" in source
        assert "_build_chart_ai_full_fix_entry" in source
        assert "asyncio.Semaphore(" in source
        assert "_ai_fix_bulk_parallelism()" in source

    def test_single_modal_generation_uses_one_violation_request(self) -> None:
        """Single flow should call violation-level generator and update modal state."""
        source = inspect.getsource(ViolationsView._build_single_ai_full_fix_entry)
        assert "generate_ai_full_fix_for_violation" in source
        assert "_entry_from_ai_result" in source

    def test_apply_flow_validates_bundle_before_write(self) -> None:
        """Apply action should validate/parse editor bundle prior to write."""
        source = inspect.getsource(ViolationsView._handle_single_ai_full_fix_action)
        assert "_verify_editor_bundle" in source
        assert "Apply blocked" in source
        assert "_apply_editor_bundle" in source

    def test_bulk_apply_validation_uses_template_patch_json_fallback(self) -> None:
        """Bulk chart flow should preserve and parse structured template patches."""
        bulk_source = inspect.getsource(ViolationsView._handle_bulk_ai_full_fix_action)
        verify_source = inspect.getsource(ViolationsView._verify_editor_bundle)
        assert "template_patches_json" in bulk_source
        assert "template_patches_json" in verify_source
        assert "artifact_key" in verify_source
        assert "Verification removed. Staged bundle is ready to apply." in verify_source

    def test_apply_uses_staged_promote_when_artifact_exists(self) -> None:
        """Apply path should support staged artifact promote flow."""
        apply_source = inspect.getsource(ViolationsView._apply_editor_bundle)
        assert "promote_staged_workspace_atomic" in apply_source
        assert "artifact_key" in apply_source

    def test_no_llm_call_in_table_loading_paths(self) -> None:
        """Loading violations table should not trigger LLM generation."""
        update_source = inspect.getsource(ViolationsView.update_data)
        no_chart_source = inspect.getsource(ViolationsView._show_no_charts_state)
        no_violation_source = inspect.getsource(ViolationsView._show_no_violations_state)
        assert "generate_ai_full_fix_for_chart" not in update_source
        assert "generate_ai_full_fix_for_violation" not in update_source
        assert "generate_ai_full_fix_for_chart" not in no_chart_source
        assert "generate_ai_full_fix_for_chart" not in no_violation_source

    def test_ai_modal_classes_exist_for_single_and_bulk(self) -> None:
        """Dedicated AI modal classes should be available for single and bulk dialogs."""
        assert AIFullFixModal is not None
        assert AIFullFixBulkModal is not None

    def test_bulk_modal_exposes_raw_llm_output_action(self) -> None:
        """Bulk modal should provide action to inspect raw provider output."""
        source = inspect.getsource(AIFullFixBulkModal.compose)
        assert "ai-full-fix-bulk-raw-llm" in source
