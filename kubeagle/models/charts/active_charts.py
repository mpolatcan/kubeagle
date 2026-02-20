"""Active charts loading and caching utilities."""

import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)


@lru_cache(maxsize=128)
def _load_active_charts_cached(file_path: str) -> frozenset[str] | None:
    """Cached loader that uses string path for hashability.

    Args:
        file_path: String path to the active charts file.

    Returns:
        frozenset of active chart names, or None if file cannot be read.
    """
    path = Path(file_path)
    try:
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as f:
            charts = frozenset(
                s for line in f if (s := line.strip()) and not s.startswith("#")
            )
        return charts or None
    except Exception as e:
        logger.error("Failed to load active charts from %s: %s", file_path, e)
        return None


def load_active_charts_from_file(file_path: Path) -> frozenset[str] | None:
    """Load active chart names from a file (one chart name per line).

    Args:
        file_path: Path to the active charts file.

    Returns:
        frozenset of active chart names, or None if file cannot be read.
    """
    return _load_active_charts_cached(str(file_path))


def get_active_charts_set(file_path: Path | None) -> frozenset[str]:
    """Get active charts as a frozenset from a file path.

    Args:
        file_path: Path to the active charts file, or None.

    Returns:
        frozenset of active chart names (empty if file not provided or invalid).
    """
    if file_path is None:
        return frozenset()
    result = load_active_charts_from_file(file_path)
    return result or frozenset()
