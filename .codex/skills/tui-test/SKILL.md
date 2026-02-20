---
name: tui-test
description: Run Textual TUI tests with appropriate per-test and global timeouts after code changes, with support for smoke-only, unit-only, or full test execution.
---

# TUI Test

Run TUI tests with `pytest-xdist` parallel execution.

## Commands

```bash
# Smoke tests only
source venv/bin/activate && timeout 60 pytest -m smoke kubeagle/tests/tui/smoke/ -n 2 -v --tb=short --timeout=30

# Unit tests only
source venv/bin/activate && timeout 120 pytest kubeagle/tests/tui/unit/ -n 2 -v --asyncio-mode=auto --timeout=30 --tb=short

# All TUI tests
source venv/bin/activate && timeout 120 pytest kubeagle/tests/tui/ -n 2 -v --asyncio-mode=auto --timeout=30 --tb=short
```

## Timeouts

| Type | Per-test | Global |
|------|----------|--------|
| Smoke | 30s | 60s |
| Unit | 30s | 120s |

Kill stuck runs when needed:

```bash
pkill -f pytest
```
