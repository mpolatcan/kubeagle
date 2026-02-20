---
name: visual-analysis
description: Capture and analyze TUI screenshots for UX review, freeze detection, and visual verification, including prompt generation and structured analysis types.
---

# Visual Analysis

Capture TUI screenshots and generate analysis prompts.

## Quick Start

```bash
source venv/bin/activate
CAPTURE_TUI="PYTHONPATH=.codex/skills/visual-analysis python -m tui_screenshot_capture"

# Capture with analysis
$CAPTURE_TUI capture <screen> --analyze --id <session-id> --charts-path ../web-helm-repository
```

Use `view_image` for rendered PNG inspection when needed.

Mandatory options:
- `--charts-path ../web-helm-repository`
- `--id <session-id>`

## Analysis Types

| Type | Purpose |
|------|---------|
| `quick` | Fast render check (5s) |
| `standard` | Normal check with expected elements (10s) |
| `data` | Data loading verification (10s) |
| `freeze` | Detect stuck/frozen states (30,60,90s) |
| `layout` | Component sizing and proportions (10s) |
| `full` | Comprehensive UX audit (default, 10s) |

## Key Options

```bash
$CAPTURE_TUI capture <screen> [OPTIONS]
$CAPTURE_TUI capture --all [OPTIONS]
$CAPTURE_TUI generate-prompt <screen> --type <type>
```

| Option | Description |
|--------|-------------|
| `--all` | Capture all screens |
| `--delays` | Comma-separated delays in seconds (default: 5) |
| `--analyze` | Generate analysis prompts |
| `--analysis-type` | Analysis type (default: full) |
| `--output` | Output directory (default: /tmp/screenshots) |
| `--id` | Session identifier (for grouping artifacts) |
| `--charts-path` | Path to helm charts (required) |

## Freeze Detection

```bash
$CAPTURE_TUI capture <screen> --delays 30,60,90 --analyze --analysis-type freeze --id <session-id> --charts-path ../web-helm-repository
```

Cleanup when done:

```bash
rm -rf /tmp/screenshots/
```
