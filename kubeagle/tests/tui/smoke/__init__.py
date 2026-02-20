"""Smoke tests package for TUI runtime verification.

Smoke tests verify:
1. TUI starts without runtime errors
2. All screens load successfully
3. Widget imports work correctly
4. No runtime exceptions during screen transitions

Usage:
    pytest -m smoke kubeagle/tests/tui/smoke/ -v
"""
