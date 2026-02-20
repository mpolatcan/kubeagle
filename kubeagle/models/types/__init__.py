"""Common types package for the TUI application.

This package consolidates shared dataclass types used across:
- controllers/
- screens/mixins/
- widgets/

Modules:
- loading: LoadingProgress and LoadResult types
- columns: ColumnDef for DataTable definitions
"""

from kubeagle.models.types.columns import ColumnDef
from kubeagle.models.types.loading import LoadingProgress, LoadResult

__all__ = ["ColumnDef", "LoadResult", "LoadingProgress"]
