"""DataTable-specific keyboard bindings.

This module contains bindings for DataTable widgets including
sorting and selection actions.
"""

from typing import Annotated

# ============================================================================
# DataTable Bindings
# ============================================================================

DATA_TABLE_BINDINGS: list[
    Annotated[tuple[str, str, str], "key, action, description"]
] = [
    ("s", "toggle_sort", "Sort"),
]

__all__ = [
    "DATA_TABLE_BINDINGS",
]
