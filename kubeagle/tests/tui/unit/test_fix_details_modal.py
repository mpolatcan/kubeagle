"""Unit tests for diff styling in fix details modal."""

from __future__ import annotations

import pytest

from kubeagle.screens.detail.components.fix_details_modal import (
    _style_diff_line,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("line", "expected_style"),
    [
        ("--- a/templates/pdb.yaml", "bold cyan"),
        ("+++ b/templates/pdb.yaml", "bold cyan"),
        ("@@ -1,4 +1,4 @@", "bold magenta"),
        ("- minAvailable: 1", "red"),
        ("+ minAvailable: 2", "green"),
        ("  selector:", ""),
    ],
)
def test_style_diff_line_color_mapping(line: str, expected_style: str) -> None:
    """Unified diff lines should map to stable, readable style buckets."""
    rendered = _style_diff_line(line)
    assert str(rendered.style) == expected_style
