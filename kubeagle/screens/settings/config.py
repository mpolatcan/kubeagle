"""Settings screen configuration - constants and UI labels."""

from __future__ import annotations

# Section headers
SECTION_GENERAL = "General Settings"
SECTION_THRESHOLDS = "Alert Thresholds"
SECTION_CLUSTER = "Cluster Settings"

# Button labels
BUTTON_SAVE = "Save"
BUTTON_CANCEL = "Cancel"
BUTTON_RESET = "Reset Defaults"

# Placeholder values
PLACEHOLDER_CHARTS_PATH = "/path/to/charts"
PLACEHOLDER_ACTIVE_CHARTS = "/path/to/active-charts.txt"
PLACEHOLDER_CODEOWNERS = "/path/to/CODEOWNERS"
PLACEHOLDER_REFRESH_INTERVAL = "30"
PLACEHOLDER_EXPORT_PATH = "/path/to/export"
PLACEHOLDER_EVENT_AGE = "24"
PLACEHOLDER_THRESHOLD = "80"
PLACEHOLDER_LIMIT_REQUEST = "2.0"
PLACEHOLDER_AI_FIX_PROVIDER = "codex"
PLACEHOLDER_AI_FIX_CODEX_MODEL = "auto"
PLACEHOLDER_AI_FIX_CLAUDE_MODEL = "auto"
PLACEHOLDER_AI_FIX_FULL_FIX_SYSTEM_PROMPT = "Edit optimizer system prompt template"

# Setting IDs
SETTING_CHARTS_PATH = "charts-path-input"
SETTING_ACTIVE_CHARTS = "active-charts-input"
SETTING_CODEOWNERS = "codeowners-input"
SETTING_REFRESH_INTERVAL = "refresh-interval-input"
SETTING_AUTO_REFRESH = "auto-refresh-switch"
SETTING_EXPORT_PATH = "export-path-input"
SETTING_EVENT_AGE = "event-age-input"
SETTING_HIGH_CPU = "high-cpu-input"
SETTING_HIGH_MEMORY = "high-memory-input"
SETTING_HIGH_POD = "high-pod-input"
SETTING_LIMIT_REQUEST = "limit-request-input"
SETTING_HIGH_POD_PERCENT = "high-pod-percent-input"
SETTING_USE_CLUSTER_VALUES = "use-cluster-values-switch"
SETTING_USE_CLUSTER_MODE = "use-cluster-mode-switch"
SETTING_AI_FIX_PROVIDER = "ai-fix-llm-provider-select"
SETTING_AI_FIX_CODEX_MODEL = "ai-fix-codex-model-select"
SETTING_AI_FIX_CLAUDE_MODEL = "ai-fix-claude-model-select"
SETTING_AI_FIX_FULL_FIX_SYSTEM_PROMPT = "ai-fix-full-fix-prompt-input"

# Validation limits
REFRESH_INTERVAL_MIN = 5
THRESHOLD_MIN = 1
THRESHOLD_MAX = 100
