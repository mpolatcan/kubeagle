"""Loading progress and result types.

Consolidated from:
- controllers/base/base_controller.py
- screens/mixins/screen_data_loader.py
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LoadingProgress:
    """Progress update for async loading operations.

    Attributes:
        phase: Current phase of the loading operation.
        progress: Progress value between 0.0 and 1.0.
        message: Human-readable status message.
        details: Optional dictionary with additional details.
    """

    phase: str
    progress: float  # 0.0 to 1.0
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class LoadResult:
    """Result wrapper for load operations.

    Attributes:
        success: Whether the load operation succeeded.
        data: The loaded data on success.
        error: Error message on failure.
        duration_ms: Time taken for the operation in milliseconds.
        from_cache: Whether the data was served from cache.
    """

    success: bool
    data: Any | None = None
    error: str | None = None
    duration_ms: float = 0.0
    from_cache: bool = False
