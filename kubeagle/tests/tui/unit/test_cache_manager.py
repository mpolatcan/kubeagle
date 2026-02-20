"""Tests for CacheManager - centralized cache coordination.

This module tests:
- CacheManager register/invalidate operations
- Pattern-based invalidation
- Related cache invalidation
- Cache statistics
"""

from __future__ import annotations

import asyncio

import pytest

from kubeagle.models.cache.data_cache import DataCache
from kubeagle.utils.cache_manager import CacheManager

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def fresh_cache_manager() -> CacheManager:
    """Get a fresh CacheManager instance for testing."""
    # Reset singleton for each test
    CacheManager._instance = None
    CacheManager._lock = asyncio.Lock()
    manager = CacheManager()
    manager._initialized = False
    manager.__init__()
    return manager


@pytest.fixture
async def sample_data_cache() -> DataCache:
    """Create a sample DataCache for testing."""
    cache = DataCache()
    # Add some test data
    await cache.set("key1", {"data": "value1"}, ttl=300)
    await cache.set("key2", {"data": "value2"}, ttl=300)
    return cache


# =============================================================================
# CacheManager Unit Tests
# =============================================================================


class TestCacheManagerImports:
    """Test that CacheManager can be imported correctly."""

    def test_cache_manager_import(self) -> None:
        """Test CacheManager class import."""
        from kubeagle.utils.cache_manager import CacheManager

        assert CacheManager is not None
        assert hasattr(CacheManager, "register")
        assert hasattr(CacheManager, "invalidate")
        assert hasattr(CacheManager, "get_cache")

    def test_cache_entry_import(self) -> None:
        """Test CacheEntry dataclass import."""
        from unittest.mock import MagicMock

        from kubeagle.utils.cache_manager import CacheEntry

        entry = CacheEntry(name="test", cache=MagicMock())
        assert entry.name == "test"

    def test_cache_stats_import(self) -> None:
        """Test CacheStats dataclass import."""
        from kubeagle.utils.cache_manager import CacheStats

        stats = CacheStats(total_entries=5, total_keys=10)
        assert stats.total_entries == 5
        assert stats.total_keys == 10

    def test_global_cache_manager_import(self) -> None:
        """Test global cache_manager instance import."""
        from kubeagle.utils import cache_manager

        assert cache_manager is not None

    def test_get_cache_manager_function(self) -> None:
        """Test get_cache_manager function."""
        from kubeagle.utils.cache_manager import (
            cache_manager,
            get_cache_manager,
        )

        result = get_cache_manager()
        assert result is cache_manager


class TestCacheManagerSingleton:
    """Test CacheManager singleton pattern."""

    def test_singleton_returns_same_instance(self) -> None:
        """Test that singleton returns the same instance."""
        # Reset singleton
        CacheManager._instance = None

        manager1 = CacheManager()
        manager2 = CacheManager()

        assert manager1 is manager2

    def test_singleton_initialized_once(self) -> None:
        """Test that singleton is initialized only once."""
        # Reset singleton
        CacheManager._instance = None

        manager = CacheManager()
        manager._initialized = False

        # Create again
        manager2 = CacheManager()

        # Should be the same instance
        assert manager is manager2


class TestCacheManagerRegistration:
    """Test CacheManager cache registration."""

    def test_register_cache(self, fresh_cache_manager: CacheManager) -> None:
        """Test registering a cache."""
        cache = DataCache()

        fresh_cache_manager.register("test_cache", cache, ttl_seconds=600)

        assert "test_cache" in fresh_cache_manager._entries

    def test_register_with_ttl(self, fresh_cache_manager: CacheManager) -> None:
        """Test registering a cache with custom TTL."""
        cache = DataCache()

        fresh_cache_manager.register("test_cache", cache, ttl_seconds=120)

        entry = fresh_cache_manager._entries["test_cache"]
        assert entry.ttl_seconds == 120

    def test_register_with_invalidator(
        self, fresh_cache_manager: CacheManager
    ) -> None:
        """Test registering a cache with invalidator."""
        from unittest.mock import AsyncMock

        cache = DataCache()
        invalidator = AsyncMock()

        fresh_cache_manager.register("test_cache", cache, invalidator=invalidator)

        entry = fresh_cache_manager._entries["test_cache"]
        assert entry.invalidator is invalidator

    def test_register_adds_to_invalidation_order(
        self, fresh_cache_manager: CacheManager
    ) -> None:
        """Test that registration adds to invalidation order."""
        cache = DataCache()

        fresh_cache_manager.register("test_cache", cache)

        assert "test_cache" in fresh_cache_manager._invalidation_order

    def test_unregister_cache(self, fresh_cache_manager: CacheManager) -> None:
        """Test unregistering a cache."""
        cache = DataCache()
        fresh_cache_manager.register("test_cache", cache)
        fresh_cache_manager._invalidation_order = ["test_cache"]

        fresh_cache_manager.unregister("test_cache")

        assert "test_cache" not in fresh_cache_manager._entries
        assert "test_cache" not in fresh_cache_manager._invalidation_order


class TestCacheManagerRetrieval:
    """Test CacheManager cache retrieval."""

    def test_get_cache(self, fresh_cache_manager: CacheManager) -> None:
        """Test getting a registered cache."""
        cache = DataCache()
        fresh_cache_manager.register("test_cache", cache)

        result = fresh_cache_manager.get_cache("test_cache")

        assert result is cache

    def test_get_cache_not_found(self, fresh_cache_manager: CacheManager) -> None:
        """Test getting a non-existent cache returns None."""
        result = fresh_cache_manager.get_cache("nonexistent")

        assert result is None

    def test_get_ttl(self, fresh_cache_manager: CacheManager) -> None:
        """Test getting TTL for a cache."""
        cache = DataCache()
        fresh_cache_manager.register("test_cache", cache, ttl_seconds=300)

        ttl = fresh_cache_manager.get_ttl("test_cache")

        assert ttl == 300

    def test_get_ttl_not_found(self, fresh_cache_manager: CacheManager) -> None:
        """Test getting TTL for non-existent cache returns None."""
        ttl = fresh_cache_manager.get_ttl("nonexistent")

        assert ttl is None


class TestCacheManagerInvalidation:
    """Test CacheManager cache invalidation."""

    @pytest.mark.asyncio
    async def test_invalidate_cache(self, fresh_cache_manager: CacheManager) -> None:
        """Test invalidating a specific cache."""
        cache = DataCache()
        await cache.set("key1", {"data": "value1"}, ttl=300)
        fresh_cache_manager.register("test_cache", cache)

        await fresh_cache_manager.invalidate("test_cache")

        # Cache should be cleared (get returns None)
        assert await cache.get("key1") is None

    @pytest.mark.asyncio
    async def test_invalidate_not_found_logs_warning(
        self, fresh_cache_manager: CacheManager
    ) -> None:
        """Test invalidating non-existent cache logs a warning."""
        from unittest.mock import patch

        with patch(
            "kubeagle.utils.cache_manager.logger"
        ) as mock_logger:
            await fresh_cache_manager.invalidate("nonexistent")

            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_invalidate_pattern(self, fresh_cache_manager: CacheManager) -> None:
        """Test invalidating caches matching a pattern."""
        cache1 = DataCache()
        cache2 = DataCache()
        await cache1.set("key", "value", ttl=300)
        await cache2.set("key", "value", ttl=300)
        fresh_cache_manager.register("charts_main", cache1)
        fresh_cache_manager.register("charts_cluster", cache2)

        await fresh_cache_manager.invalidate_pattern("charts*")

        # Both caches should be cleared
        assert await cache1.get("key") is None
        assert await cache2.get("key") is None

    @pytest.mark.asyncio
    async def test_invalidate_pattern_wildcard(
        self, fresh_cache_manager: CacheManager
    ) -> None:
        """Test invalidating all caches with wildcard."""
        cache1 = DataCache()
        cache2 = DataCache()
        fresh_cache_manager.register("cache1", cache1)
        fresh_cache_manager.register("cache2", cache2)

        await fresh_cache_manager.invalidate_pattern("*")

        # Both should be cleared
        assert await cache1.get("key") is None
        assert await cache2.get("key") is None

    @pytest.mark.asyncio
    async def test_invalidate_all(self, fresh_cache_manager: CacheManager) -> None:
        """Test invalidating all caches."""
        cache1 = DataCache()
        cache2 = DataCache()
        fresh_cache_manager.register("cache1", cache1)
        fresh_cache_manager.register("cache2", cache2)

        await fresh_cache_manager.invalidate_all()

        assert await cache1.get("key") is None
        assert await cache2.get("key") is None

    @pytest.mark.asyncio
    async def test_invalidate_all_calls_invalidators(
        self, fresh_cache_manager: CacheManager
    ) -> None:
        """Test invalidate_all calls registered invalidators."""
        from unittest.mock import AsyncMock

        cache = DataCache()
        invalidator = AsyncMock()
        fresh_cache_manager.register("test_cache", cache, invalidator=invalidator)

        await fresh_cache_manager.invalidate_all()

        invalidator.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_related(self, fresh_cache_manager: CacheManager) -> None:
        """Test invalidating related caches."""
        cache_charts = DataCache()
        cache_releases = DataCache()
        fresh_cache_manager.register("charts", cache_charts)
        fresh_cache_manager.register("releases", cache_releases)

        await fresh_cache_manager.invalidate_related(["charts"])

        # Both should be cleared due to relationship
        assert await cache_charts.get("key") is None
        assert await cache_releases.get("key") is None


class TestCacheManagerStatistics:
    """Test CacheManager statistics."""

    def test_get_stats_empty(self, fresh_cache_manager: CacheManager) -> None:
        """Test getting stats for empty manager."""
        stats = fresh_cache_manager.get_stats()

        assert stats.total_entries == 0
        assert stats.total_keys == 0
        assert stats.entries == {}

    def test_get_stats_with_entries(self, fresh_cache_manager: CacheManager) -> None:
        """Test getting stats with registered caches."""
        cache = DataCache()
        fresh_cache_manager.register("test_cache", cache, ttl_seconds=300)

        stats = fresh_cache_manager.get_stats()

        assert stats.total_entries == 1
        assert "test_cache" in stats.entries
        assert stats.entries["test_cache"]["ttl_seconds"] == 300

    def test_list_registered(self, fresh_cache_manager: CacheManager) -> None:
        """Test listing registered cache names."""
        cache1 = DataCache()
        cache2 = DataCache()
        fresh_cache_manager.register("cache1", cache1)
        fresh_cache_manager.register("cache2", cache2)

        names = fresh_cache_manager.list_registered()

        assert len(names) == 2
        assert "cache1" in names
        assert "cache2" in names


class TestCacheManagerPolicyHelpers:
    """Test CacheManager cache policy helpers."""

    @pytest.mark.asyncio
    async def test_refresh_if_stale_cache_not_found(
        self, fresh_cache_manager: CacheManager
    ) -> None:
        """Test refresh_if_stale when cache is not registered."""
        from unittest.mock import AsyncMock

        fetch_fn = AsyncMock(return_value="fresh data")

        result = await fresh_cache_manager.refresh_if_stale(
            cache_name="nonexistent",
            key="test_key",
            max_age_seconds=60.0,
            fetch_fn=fetch_fn,
        )

        fetch_fn.assert_called_once()
        assert result == "fresh data"

    @pytest.mark.asyncio
    async def test_refresh_if_stale_calls_fetch(
        self, fresh_cache_manager: CacheManager
    ) -> None:
        """Test refresh_if_stale calls fetch function when cache is stale."""
        from unittest.mock import AsyncMock

        cache = DataCache()
        fresh_cache_manager.register("test_cache", cache)
        fetch_fn = AsyncMock(return_value="fresh data")

        # Since we can't easily check cache age, it should call fetch_fn
        result = await fresh_cache_manager.refresh_if_stale(
            cache_name="test_cache",
            key="test_key",
            max_age_seconds=60.0,
            fetch_fn=fetch_fn,
        )

        # Fetch is called because we can't determine cache age
        fetch_fn.assert_called_once()
        assert result == "fresh data"


# =============================================================================
# Exports
# =============================================================================


__all__ = [
    "TestCacheManagerImports",
    "TestCacheManagerSingleton",
    "TestCacheManagerRegistration",
    "TestCacheManagerRetrieval",
    "TestCacheManagerInvalidation",
    "TestCacheManagerStatistics",
    "TestCacheManagerPolicyHelpers",
]
