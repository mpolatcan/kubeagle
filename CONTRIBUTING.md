# Contributing to KubEagle

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Development Setup

### Prerequisites

- Python 3.10 or higher
- pip or poetry for dependency management

### Installation

```bash
# Clone the repository
git clone https://github.com/mpolatcan/kubeagle.git
cd kubeagle

# Install dependencies
pip install -e ".[dev]"

# Or using poetry
poetry install --with dev
```

## Testing

### Test Organization

Tests are organized in the `kubeagle/tests/` directory:

```
tests/
├── tui/
│   ├── unit/           # Unit tests (models, controllers, widgets, optimizer)
│   │   ├── test_models_unit.py
│   │   ├── test_controllers_unit.py
│   │   ├── test_widgets.py
│   │   ├── test_optimizer_unit.py
│   │   └── test_screens_unit.py
│   ├── visual/         # Visual/snapshot tests
│   │   ├── test_home_screen.py
│   │   ├── test_charts_screen.py
│   │   └── ...
│   ├── conftest.py     # Pytest fixtures
│   └── tui/
│       └── conftest.py
```

### Pytest Markers

The project uses pytest markers to categorize and filter tests:

| Marker | Description | Usage |
|--------|-------------|-------|
| `unit` | Unit tests for models, controllers, optimizer rules | `@pytest.mark.unit` |
| `fast` | Tests completing in <100ms (default quick validation) | `@pytest.mark.fast` |
| `slow` | Tests taking >100ms (excluded by default) | `@pytest.mark.slow` |
| `visual` | Visual regression tests using pytest-textual-snapshot | `@pytest.mark.visual` |
| `snapshot` | Snapshot tests for UI comparisons | `@pytest.mark.snapshot` |
| `integration` | Integration tests with mocked K8s API boundaries | `@pytest.mark.integration` |

### Running Tests

```bash
# Run all tests (slow tests excluded by default)
pytest

# Run only fast unit tests (recommended for quick validation)
pytest -m "fast"

# Run all tests including slow tests
pytest -m "slow"

# Run visual/snapshot tests
pytest -m "visual"

# Run tests without any marker filtering
pytest -m "not slow"

# Run with verbose output
pytest -v

# Run specific test file
pytest kubeagle/tests/tui/unit/test_models_unit.py

# Run specific test class
pytest kubeagle/tests/tui/unit/test_models_unit.py::TestChartInfo

# Run specific test
pytest kubeagle/tests/tui/unit/test_models_unit.py::TestChartInfo::test_chart_info_creation
```

### Default Behavior

By default, pytest is configured to skip slow tests:

```toml
# In pyproject.toml
[tool.pytest.ini_options]
addopts = "-n auto --dist loadfile -m \"not slow\""
```

This means:
- `pytest` runs only `fast` and `unit` tests
- `pytest -m "fast"` runs quick validation tests
- `pytest -m "slow"` runs only the slow tests
- `pytest -m "not slow"` runs all tests

### Writing Tests

#### Unit Tests

Unit tests should:
- Test a single unit of functionality
- Complete in <100ms
- Use mocking to avoid external dependencies
- Be marked with `@pytest.mark.unit` and `@pytest.mark.fast`

```python
@pytest.mark.unit
@pytest.mark.fast
class TestMyFeature:
    def test_feature_behavior(self):
        # Test implementation
        assert expected_result == actual_result
```

#### Async Tests

For async code, use `pytest-asyncio`:

```python
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.asyncio
async def test_async_feature():
    result = await some_async_function()
    assert result == expected
```

#### Visual Tests

Visual tests should be marked with `@pytest.mark.visual`:

```python
@pytest.mark.visual
@pytest.mark.snapshot
def test_screen_rendering(snapshot_compare):
    app = EKSHelmReporterApp()
    # Test visual rendering
    snapshot_compare(app)
```

## Code Style

### Linting

```bash
# Run ruff linter
ruff check .

# Fix auto-fixable issues
ruff check --fix .
```

### Type Checking

```bash
# Run ty type checker (Astral's fast type checker)
ty check eks_helm_reporter/ kubeagle/ .claude/skills/visual-analysis/tui_screenshot_capture/
```

### Formatting

```bash
# Format code with ruff
ruff format .
```

## Pull Request Process

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/my-feature`
3. **Make** your changes
4. **Run** tests: `pytest -m "fast"` (quick validation)
5. **Run** linting: `ruff check .`
6. **Run** type checking: `ty check eks_helm_reporter/ kubeagle/ .claude/skills/visual-analysis/tui_screenshot_capture/`
7. **Submit** a pull request

### PR Requirements

- All fast tests must pass
- No linting errors
- No type errors
- Tests added for new functionality (if applicable)
- Documentation updated (if applicable)

## Project Structure

```
kubeagle/
├── eks_helm_reporter/          # CLI source
│   ├── cli.py
│   └── models/
├── kubeagle/      # TUI source
│   ├── app.py
│   ├── main.py
│   ├── screens/
│   ├── widgets/
│   ├── controllers/
│   ├── models/
│   ├── optimizer/
│   ├── utils/
│   ├── keyboard.py
│   └── tests/
├── docs/                        # Documentation
├── pyproject.toml               # Project configuration
└── README_TUI.md
```

## Getting Help

- Open an [issue](https://github.com/mpolatcan/kubeagle/issues) for bugs or feature requests
- Check existing issues before creating a new one
- Follow the issue template when reporting bugs
