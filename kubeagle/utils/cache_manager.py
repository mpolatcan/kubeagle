"""CacheManager - Centralized cache coordination for data loading.

This module provides CacheManager, a singleton for coordinating cache
invalidation across all controllers.

Usage:
    from kubeagle.utils.cache_manager import cache_manager

    # Get a controller's cache
    cache = cache_manager.get_controller_cache("charts")

    # Invalidate all caches
    await cache_manager.invalidate_all()

    # Get cache statistics
    stats = cache_manager.get_cache_stats()
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from kubeagle.models.cache.data_cache import DataCache

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with metadata."""

    name: str
    cache: DataCache
    ttl_seconds: int = 300
    invalidator: Callable[[], Awaitable[None]] | None = None


@dataclass
class CacheStats:
    """Cache statistics."""

    total_entries: int = 0
    total_keys: int = 0
    entries: dict[str, dict[str, Any]] = field(default_factory=dict)


class CacheManager:
    """Singleton cache manager for coordinating cache invalidation.

    This manager:
    - Registers caches from different controllers
    - Provides coordinated invalidation
    - Tracks cache statistics
    - Supports TTL policies per cache type

    Usage:
        cache_manager = CacheManager()

        # Register a controller cache
        cache_manager.register("charts", DataCache())

        # Get cache for a controller
        cache = cache_manager.get_cache("charts")

        # Invalidate all caches
        await cache_manager.invalidate_all()

        # Invalidate specific pattern
        await cache_manager.invalidate_pattern("charts*")
    """

    _instance: CacheManager | None = None
    _lock = asyncio.Lock()

    def __new__(cls) -> CacheManager:
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize the CacheManager (singleton)."""
        if self._initialized:
            return

        self._entries: dict[str, CacheEntry] = {}
        self._invalidation_order: list[str] = []
        self._initialized = True

        logger.info("CacheManager initialized")

    # =========================================================================
    # Registration
    # =========================================================================

    def register(
        self,
        name: str,
        cache: DataCache,
        ttl_seconds: int = 300,
        invalidator: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        """Register a controller's cache.

        Args:
            name: Unique name for the cache (e.g., "charts", "cluster")
            cache: DataCache instance
            ttl_seconds: Default TTL for entries in this cache
            invalidator: Optional async function to call on full invalidation
        """
        self._entries[name] = CacheEntry(
            name=name,
            cache=cache,
            ttl_seconds=ttl_seconds,
            invalidator=invalidator,
        )

        if name not in self._invalidation_order:
            self._invalidation_order.append(name)

        logger.debug(f"Registered cache: {name} (TTL={ttl_seconds}s)")

    def unregister(self, name: str) -> None:
        """Unregister a cache.

        Args:
            name: Name of the cache to unregister
        """
        if name in self._entries:
            del self._entries[name]
            self._invalidation_order = [n for n in self._invalidation_order if n != name]
            logger.debug(f"Unregistered cache: {name}")

    def get_cache(self, name: str) -> DataCache | None:
        """Get a registered cache.

        Args:
            name: Name of the cache

        Returns:
            DataCache instance or None if not registered
        """
        entry = self._entries.get(name)
        return entry.cache if entry else None

    def get_ttl(self, name: str) -> int | None:
        """Get TTL for a cache.

        Args:
            name: Name of the cache

        Returns:
            TTL in seconds or None if not registered
        """
        entry = self._entries.get(name)
        return entry.ttl_seconds if entry else None

    # =========================================================================
    # Invalidation
    # =========================================================================

    async def invalidate(self, name: str) -> None:
        """Invalidate a specific cache.

        Args:
            name: Name of the cache to invalidate
        """
        entry = self._entries.get(name)
        if entry:
            await entry.cache.clear()
            logger.debug(f"Invalidated cache: {name}")
        else:
            logger.warning(f"Cache not found for invalidation: {name}")

    async def invalidate_pattern(self, pattern: str) -> None:
        """Invalidate caches matching a pattern.

        Args:
            pattern: Glob-style pattern (e.g., "charts*", "*")
        """
        import fnmatch

        matched = [
            name for name in self._entries
            if fnmatch.fnmatch(name, pattern)
        ]

        for name in matched:
            await self.invalidate(name)

        logger.debug(f"Invalidated {len(matched)} caches matching: {pattern}")

    async def invalidate_all(self) -> None:
        """Invalidate all registered caches.

        Calls any registered invalidators and clears all caches.
        """
        # Call invalidators first
        for entry in self._entries.values():
            if entry.invalidator is not None:
                try:
                    await entry.invalidator()
                except Exception as e:
                    logger.exception(f"Invalidator failed for {entry.name}: {e}")

        # Clear all caches
        for name in self._invalidation_order:
            entry = self._entries.get(name)
            if entry:
                await entry.cache.clear()

        logger.info(f"Invalidated all {len(self._entries)} caches")

    async def invalidate_related(self, names: list[str]) -> None:
        """Invalidate caches related to specific names.

        This is useful when data changes might affect multiple caches.

        Args:
            names: List of cache names that might have related caches
        """
        # Define relationships between caches
        relationships: dict[str, list[str]] = {
            "charts": ["charts_cluster", "releases"],
            "charts_cluster": ["charts", "releases"],
            "releases": ["charts_cluster"],
            "nodes": ["pods", "events"],
            "pods": ["events"],
        }

        # Collect all related caches
        to_invalidate: set[str] = set()

        for name in names:
            to_invalidate.add(name)
            related = relationships.get(name, [])
            to_invalidate.update(related)

        # Invalidate all
        for name in to_invalidate:
            await self.invalidate(name)

        logger.debug(f"Invalidated related caches: {to_invalidate}")

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> CacheStats:
        """Get cache statistics.

        Returns:
            CacheStats with current statistics
        """
        entries: dict[str, dict[str, Any]] = {}
        total_keys = 0

        for name, entry in self._entries.items():
            # Get cache info without accessing internals
            entries[name] = {
                "ttl_seconds": entry.ttl_seconds,
                "has_invalidator": entry.invalidator is not None,
            }
            # Note: We can't get exact key count without exposing internals
            total_keys += 1  # Approximation

        return CacheStats(
            total_entries=len(self._entries),
            total_keys=total_keys,
            entries=entries,
        )

    def list_registered(self) -> list[str]:
        """List all registered cache names.

        Returns:
            List of cache names
        """
        return list(self._entries)

    # =========================================================================
    # Cache Policy Helpers
    # =========================================================================

    async def refresh_if_stale(
        self,
        cache_name: str,
        key: str,
        max_age_seconds: float,
        fetch_fn: Callable[[], Awaitable[Any]],
    ) -> Any:
        """Fetch data if cache is stale.

        Args:
            cache_name: Name of the cache
            key: Cache key
            max_age_seconds: Maximum age in seconds before refresh
            fetch_fn: Async function to fetch fresh data

        Returns:
            Cached or fresh data
        """

        cache = self.get_cache(cache_name)
        if cache is None:
            return await fetch_fn()

        # Check if cache is fresh enough
        # This is a simplified check - full implementation would need
        # access to cache internals

        # For now, always fetch fresh if we can't determine age
        return await fetch_fn()


# Global cache manager instance
cache_manager = CacheManager()


def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance.

    Returns:
        CacheManager singleton instance
    """
    return cache_manager


__all__ = [
    "CacheManager",
    "CacheEntry",
    "CacheStats",
    "cache_manager",
    "get_cache_manager",
]
