---
name: visual-analysis
description: Complete visual analysis workflow - screenshot capture with automatic PNG conversion, AI vision analysis. Use for UX review, freeze detection, and visual verification.
argument-hint: "[screen...] [--analyze] [--analysis-type quick|standard|freeze]"
allowed-tools: Bash, Glob, Grep, Read
---

# Visual Analysis Skill

## Quick Start

```bash
source venv/bin/activate
CAPTURE_TUI="PYTHONPATH=.claude/skills/visual-analysis python -m tui_screenshot_capture"

# Capture with analysis
$CAPTURE_TUI capture <screen> --analyze --charts-path ../web-helm-repository

# Then read screenshot natively (Claude Code is multimodal)
Read(file_path="/tmp/screenshots/<screen>/<screen>-010s.png")
```

**MANDATORY**: `--charts-path ../web-helm-repository` and `--id` for organized output.

## Analysis Types

| Type | Purpose |
|------|---------|
| `quick` | Fast render check (5s) |
| `standard` | Normal check with expected elements (10s) |
| `data` | Data loading verification (10s) |
| `freeze` | Detect stuck/frozen states (30,60,90s) |
| `layout` | Component sizing and proportions (10s) |
| `full` | **Comprehensive UX audit (DEFAULT, 10s)** |

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
| `--analyze` | Generate AI analysis prompts |
| `--analysis-type` | Analysis type (default: full) |
| `--output` | Output directory (default: /tmp/screenshots) |
| `--id` | Session identifier (PRD-XXX) |
| `--charts-path` | **REQUIRED** Path to helm charts |

## Freeze Detection

```bash
$CAPTURE_TUI capture <screen> --delays 30,60,90 --analyze --analysis-type freeze --charts-path ../web-helm-repository
Read(file_path="/tmp/screenshots/<screen>/<screen>-090s.png")
```

Cleanup: `rm -rf /tmp/screenshots/`
