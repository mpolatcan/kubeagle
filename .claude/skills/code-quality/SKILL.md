---
name: code-quality
description: Run lint + typecheck together. Use after implementation, before committing, or when checking code quality.
argument-hint: "[--fix]"
allowed-tools: Bash
---

# Code Quality Check

Run ruff linter and ty type checker in one command.

## Usage

```
/code-quality
```

## Command

```bash
source venv/bin/activate && \
echo "=== LINT ===" && \
ruff check eks_helm_reporter/ kubeagle/ .claude/skills/visual-analysis/tui_screenshot_capture/ && \
echo -e "\n=== TYPECHECK (ty) ===" && \
ty check eks_helm_reporter/ kubeagle/ .claude/skills/visual-analysis/tui_screenshot_capture/
```

## Expected Output

```
=== LINT ===
All checks passed!

=== TYPECHECK (ty) ===
Found N diagnostics
```

Both checks must pass with 0 errors.
