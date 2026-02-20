---
name: code-quality
description: Run lint and type checks together after implementation and before commit to validate code quality for the CLI, TUI, and visual-analysis tooling.
---

# Code Quality Check

Run `ruff` and `ty` in one command.

```bash
source venv/bin/activate && \
echo "=== LINT ===" && \
ruff check eks_helm_reporter/ kubeagle/ .codex/skills/visual-analysis/tui_screenshot_capture/ && \
echo "\n=== TYPECHECK (ty) ===" && \
ty check eks_helm_reporter/ kubeagle/ .codex/skills/visual-analysis/tui_screenshot_capture/
```

Both checks must pass with zero errors.
