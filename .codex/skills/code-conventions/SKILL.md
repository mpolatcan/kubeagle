---
name: code-conventions
description: Run all TUI code convention checks (constants, enums, keybindings, models, inline CSS) after implementation to enforce project standards and catch misplaced patterns.
---

# Code Conventions Check

Run convention checks for `kubeagle`.

## What It Checks

| Check | Convention | Correct Location |
|-------|------------|------------------|
| Constants | UPPER_CASE values, thresholds, patterns | `constants/` |
| Enums | Enum class definitions | `constants/enums.py` |
| Keybindings | BINDINGS lists, Binding() calls | `keyboard/` |
| Models | BaseModel, dataclass, NamedTuple | `models/` |
| Inline CSS | CSS/DEFAULT_CSS class variables | `css/**/*.tcss` files |

## Instructions

Run checks in parallel when possible. Exclude `tests/` and `__pycache__/`.

### 1. Constants

```bash
rg --line-number --glob '*.py' '^[A-Z][A-Z_0-9]+\s*=' kubeagle
```

Exclude matches under `kubeagle/constants/` and `kubeagle/keyboard/`.

### 2. Enums

```bash
rg --line-number --glob '*.py' 'class\s+\w+\((str,\s*)?Enum\)' kubeagle
```

Exclude `kubeagle/constants/enums.py`.

### 3. Keybindings

```bash
rg --line-number --glob '*.py' '^\s*BINDINGS\s*=\s*\[' kubeagle
rg --line-number --glob '*.py' 'Binding\s*\(' kubeagle
```

Exclude `kubeagle/keyboard/`.

### 4. Models

```bash
rg --line-number --glob '*.py' 'class\s+\w+\(.*BaseModel.*\)' kubeagle
rg --line-number --glob '*.py' '@dataclass' kubeagle
```

Exclude `kubeagle/models/`.

### 5. Inline CSS

```bash
rg --line-number --glob '*.py' "DEFAULT_CSS\\s*=\\s*['\\\"]" kubeagle
rg --files kubeagle | rg '\\.tcss$'
```

Exclude `kubeagle/css/`.

## Report Format

```text
## SUMMARY
Total violations: [N]
Status: PASS / FAIL
```

Use architecture rules in `AGENTS.md` as the source of truth for keybinding locations.
