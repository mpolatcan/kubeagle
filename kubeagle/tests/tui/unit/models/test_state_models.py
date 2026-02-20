"""Tests for state models."""

from __future__ import annotations

from kubeagle.models.state.app_settings import AppSettings
from kubeagle.models.state.app_state import AppState


class TestAppState:
    """Tests for AppState model."""

    def test_app_state_creation(self) -> None:
        """Test AppState creation."""
        state = AppState()

        assert state.cluster_connected is False
        assert state.loading_state is not None
        assert state.error_message == ""


class TestAppSettings:
    """Tests for AppSettings model."""

    def test_app_settings_creation(self) -> None:
        """Test AppSettings creation."""
        settings = AppSettings()

        assert settings.theme == "InsiderOne-Dark"
        assert settings.refresh_interval > 0
        assert settings.optimizer_analysis_source == "auto"
        assert settings.verify_fixes_with_render is True
        assert settings.helm_template_timeout_seconds == 30
        assert settings.ai_fix_llm_provider == "codex"
        assert settings.ai_fix_codex_model == "auto"
        assert settings.ai_fix_claude_model == "auto"
        assert settings.ai_fix_full_fix_system_prompt == ""
        assert settings.ai_fix_bulk_parallelism == 2
