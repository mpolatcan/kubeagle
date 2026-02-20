---
name: tui-test
description: Run Textual TUI tests with proper timeouts. Use when running TUI unit tests or after making code changes.
argument-hint: "[smoke|unit|all]"
allowed-tools: Bash
---

# TUI Test Skill

Run Textual TUI tests with pytest-xdist parallel execution (2 workers).

## Usage

```
/tui-test [smoke|unit|all]
```

| Option | Description |
|--------|-------------|
| (none) | Run all TUI tests (unit + smoke) |
| `smoke` | Smoke tests only - fast runtime verification |
| `unit` | Unit tests only |
| `all` | Run all tests |

## Commands

```bash
# Smoke tests only (fast verification)
source venv/bin/activate && timeout 60 pytest -m smoke kubeagle/tests/tui/smoke/ -n 2 -v --tb=short --timeout=30

# All tests
source venv/bin/activate && timeout 120 pytest kubeagle/tests/tui/ -n 2 -v --asyncio-mode=auto --timeout=30 --tb=short

# Unit only
source venv/bin/activate && timeout 120 pytest kubeagle/tests/tui/unit/ -n 2 -v --asyncio-mode=auto --timeout=30 --tb=short
```

## Timeouts

| Type | Per-test | Global |
|------|----------|--------|
| Smoke | 30s | 60s |
| Unit | 30s | 120s |

## Kill Stuck Tests

```bash
pkill -f pytest
```

## Test Structure

```
kubeagle/tests/tui/
├── smoke/
│   ├── keybindings/                       # Navigation and table binding tests
│   ├── screens/                           # Per-screen smoke tests (charts/, cluster/, detail/, home/, reports/, settings/, teams/)
│   ├── test_custom_data_table_runtime.py  # Runtime data table smoke test
│   └── test_keypress_navigation.py        # Keypress navigation smoke test
└── unit/
    ├── controllers/    # Fetchers, parsers, mappers, analyzers
    ├── constants/      # Defaults, enums, limits, optimizer, patterns, screen, tables, timeouts, ui, values
    ├── models/         # State, cache, core, events, teams, optimization, reports
    ├── presenters/     # Screen presenter logic
    ├── widgets/        # Containers, data tables, display, filter, input, selection, special
    ├── optimizer/      # Analyzer, fixer, rules
    ├── config/         # Screen config tests
    ├── mixins/         # Screen mixin tests
    ├── utils/          # Resource parser, etc.
    ├── test_app.py, test_base_screen.py                          # App and base screen tests
    ├── test_cache_manager.py, test_concurrent.py                 # Utils tests at root
    ├── test_custom_data_table.py, test_footer_widget.py          # Widget tests at root
    ├── test_modularization.py, test_optimizer_unit.py            # Structure and optimizer tests
    ├── test_screen_data_loader.py, test_worker_mixin.py          # Mixin tests at root
    └── test_*_fix_regression.py                                  # Regression tests for fixes
```

Smoke tests are infrastructure (maintained by tui-test-engineer, used by tui-developer for quick verification).
For visual/UX verification, use `/visual-analysis` instead.
