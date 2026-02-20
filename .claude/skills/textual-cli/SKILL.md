---
name: textual-cli
description: Textual CLI devtools for running, debugging, and exploring TUI apps. Includes run, console, serve, keys, colors, borders, easing commands. Used by tui-developer, tui-test-engineer, and tui-ux-specialist.
argument-hint: "<command> [options]"
allowed-tools: Bash
---

# Textual CLI Skill

**Not for screenshots** - use `/visual-analysis` for capture.

## Commands

| Command | Purpose |
|---------|---------|
| `run` | Run Textual app (with optional --dev mode) |
| `run --press` | Navigate with simulated key presses |
| `console` | Debug console for print/log output |
| `serve` | Serve app in web browser |
| `keys` | Test keyboard input recognition |
| `colors` | Preview color system |
| `borders` | Preview border styles |
| `easing` | Preview animation easing functions |

## Usage

```bash
# Standard run
source venv/bin/activate && textual run kubeagle/main.py

# Dev mode (live CSS editing)
source venv/bin/activate && textual run --dev kubeagle/main.py

# With charts data
source venv/bin/activate && textual run --dev kubeagle/main.py -- --charts-path ../web-helm-repository

# Navigate with key presses
source venv/bin/activate && timeout 30 textual run kubeagle/main.py --press "c,2"
```

| Flag | Description |
|------|-------------|
| `--dev` | Enable dev mode (live CSS, console output) |
| `--press TEXT` | Comma-separated keys to simulate press |

**Do NOT** use `--screenshot` flag or `--press "q"` (hides CSS errors). Use `/visual-analysis` instead.
