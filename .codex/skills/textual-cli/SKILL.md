---
name: textual-cli
description: Use Textual CLI dev tools to run, debug, and inspect the TUI app, including dev mode, key-press simulation, console, and style preview commands.
---

# Textual CLI

Use Textual commands for local TUI development. Use `visual-analysis` skill for screenshots.

## Common Commands

```bash
# Standard run
source venv/bin/activate && textual run kubeagle/main.py

# Dev mode (live CSS editing)
source venv/bin/activate && textual run --dev kubeagle/main.py

# With charts data
source venv/bin/activate && textual run --dev kubeagle/main.py -- --charts-path ../web-helm-repository

# Navigate with key presses
source venv/bin/activate && timeout 30 textual run kubeagle/main.py --press "c,2"

# Textual utilities
source venv/bin/activate && textual console
source venv/bin/activate && textual keys
source venv/bin/activate && textual colors
source venv/bin/activate && textual borders
source venv/bin/activate && textual easing
```

Do not use `--screenshot` or `--press "q"` for visual validation. Use `visual-analysis` for capture workflows.
