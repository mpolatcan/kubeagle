---
name: code-conventions
description: Run all code convention checks (constants, enums, keybindings, models, inline CSS). Run after implementation to enforce project standards.
argument-hint: "[--check CATEGORY]"
allowed-tools: Grep, Glob, Read
---

# Code Conventions Check

Runs all convention checks using Claude Code native tools.

## Usage

```
/code-conventions
```

## What It Checks

| Check | Convention | Correct Location |
|-------|------------|------------------|
| Constants | UPPER_CASE values, thresholds, patterns | `constants/` |
| Enums | Enum class definitions | `constants/enums.py` |
| Keybindings | BINDINGS lists, Binding() calls | `keyboard/` |
| Models | BaseModel, dataclass, NamedTuple | `models/` |
| Inline CSS | CSS/DEFAULT_CSS class variables | `css/**/*.tcss` files |

## Instructions

Run ALL checks **in parallel**. Exclude: `tests/`, `__pycache__/`

### 1. CONSTANTS
```
Grep(pattern="^[A-Z][A-Z_0-9]+\\s*=", path="kubeagle", glob="*.py")
# EXCLUDE: constants/, keyboard/
```

### 2. ENUMS
```
Grep(pattern="class\\s+\\w+\\((str,\\s*)?Enum\\)", path="kubeagle", glob="*.py")
# EXCLUDE: constants/enums.py
```

### 3. KEYBINDINGS
```
Grep(pattern="^\\s*BINDINGS\\s*=\\s*\\[", path="kubeagle", glob="*.py")
Grep(pattern="Binding\\s*\\(", path="kubeagle", glob="*.py")
# EXCLUDE: keyboard/
```

### 4. MODELS
```
Grep(pattern="class\\s+\\w+\\(.*BaseModel.*\\)", path="kubeagle", glob="*.py")
Grep(pattern="@dataclass", path="kubeagle", glob="*.py")
# EXCLUDE: models/
```

### 5. INLINE CSS
```
Grep(pattern="DEFAULT_CSS\\s*=\\s*[\"']", path="kubeagle", glob="*.py")
Glob(pattern="kubeagle/**/*.tcss")
# EXCLUDE: css/
```

## Report Format

```
## SUMMARY
Total violations: [N]
Status: PASS ✓ / FAIL ✗
```

> **Keybindings**: See `architecture.md` for authoritative file locations.
> **Enums**: All enum definitions live in `constants/enums.py` (no separate `enums/` directory).
