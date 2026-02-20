"""Tests for cache models."""

from __future__ import annotations

from kubeagle.models.cache.data_cache import DataCache


class TestDataCache:
    """Tests for DataCache model."""

    def test_data_cache_creation(self) -> None:
        """Test DataCache creation."""
        cache = DataCache()

        assert cache is not None
