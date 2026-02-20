"""Data cache implementation."""

import asyncio
import time
from typing import Any


class DataCache:
    """TTL-based data caching with automatic invalidation."""

    TTL_SECONDS = {
        "nodes": 300,
        "pods": 180,
        "events": 60,
        "charts": 600,
        "releases": 120,
    }

    def __init__(self) -> None:
        self._cache: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any:
        """Get cached data or None if expired (thread-safe)."""
        async with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]
            ttl = self._get_ttl_info(key, entry)

            if ttl is not None and self._is_expired(entry, ttl):
                del self._cache[key]
                return None

            return entry["data"]

    def _get_ttl_info(self, key: str, entry: dict[str, Any]) -> int | None:
        """Get TTL value for a cache entry.

        Args:
            key: Cache key.
            entry: Cache entry containing timestamp and optional ttl.

        Returns:
            TTL in seconds or None.
        """
        return entry.get("ttl") or self.TTL_SECONDS.get(key, 300)

    def _is_expired(self, entry: dict[str, Any], ttl: int) -> bool:
        """Check if a cache entry is expired.

        Args:
            entry: Cache entry with timestamp.
            ttl: TTL in seconds.

        Returns:
            True if entry is expired.
        """
        age = time.monotonic() - entry["timestamp"]
        return age > ttl

    async def set(self, key: str, data: Any, ttl: int | None = None) -> None:
        """Cache data with current timestamp (thread-safe)."""
        async with self._lock:
            self._cache[key] = {"data": data, "timestamp": time.monotonic(), "ttl": ttl}

    async def get_if_fresh(self, key: str, max_age_seconds: float) -> Any:
        """Get cached data only if younger than max_age_seconds.

        Unlike ``get()``, this ignores the entry's own TTL and uses
        the caller-supplied *max_age_seconds* as the freshness threshold.

        Args:
            key: Cache key.
            max_age_seconds: Maximum acceptable age in seconds.

        Returns:
            Cached data if fresh enough, otherwise None.
        """
        async with self._lock:
            if key not in self._cache:
                return None
            entry = self._cache[key]
            age = time.monotonic() - entry["timestamp"]
            if age > max_age_seconds:
                return None
            return entry["data"]

    async def clear(self, key: str | None = None) -> None:
        """Clear cache for specific key or all (thread-safe)."""
        async with self._lock:
            if key:
                self._cache.pop(key, None)
            else:
                self._cache.clear()
