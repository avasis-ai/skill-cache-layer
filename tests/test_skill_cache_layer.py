"""Tests for skill-cache-layer."""

import json
import tempfile
from pathlib import Path

import pytest

from skill_cache_layer.semantic_cache import CacheEntry, SemanticCache


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_default_timestamp(self) -> None:
        """Test that timestamp is set by default."""
        entry = CacheEntry(
            query_hash="abc123",
            skill_name="test_skill",
            input_signature="test_input",
            result={"data": "test"}
        )

        assert entry.timestamp > 0
        assert entry.confidence == 1.0

    def test_custom_confidence(self) -> None:
        """Test custom confidence score."""
        entry = CacheEntry(
            query_hash="abc123",
            skill_name="test_skill",
            input_signature="test_input",
            result="test",
            confidence=0.95
        )

        assert entry.confidence == 0.95


class TestSemanticCache:
    """Tests for SemanticCache class."""

    def test_init_creates_cache(self) -> None:
        """Test cache initialization."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            cache_path = tmp.name

        try:
            cache = SemanticCache(cache_path=cache_path)
            assert cache.cache_path == Path(cache_path)
            assert len(cache._entries) == 0
        finally:
            Path(cache_path).unlink(missing_ok=True)

    def test_add_and_get_entry(self) -> None:
        """Test adding and retrieving entries."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            cache_path = tmp.name

        try:
            cache = SemanticCache(cache_path=cache_path)

            # Add entry
            cache.add(
                skill_name="test_skill",
                input_text="test input",
                result={"status": "success"},
                confidence=1.0
            )

            # Get entry
            result = cache.get("test_skill", "test input")
            assert result == {"status": "success"}
        finally:
            Path(cache_path).unlink(missing_ok=True)

    def test_cache_miss(self) -> None:
        """Test cache miss for non-existent entry."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            cache_path = tmp.name

        try:
            cache = SemanticCache(cache_path=cache_path)

            result = cache.get("nonexistent_skill", "test input")
            assert result is None
        finally:
            Path(cache_path).unlink(missing_ok=True)

    def test_cache_with_metadata(self) -> None:
        """Test retrieving cache entries with metadata."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            cache_path = tmp.name

        try:
            cache = SemanticCache(cache_path=cache_path)

            cache.add(
                skill_name="test_skill",
                input_text="test input",
                result={"data": "test"},
                confidence=0.9
            )

            result, metadata = cache.get_with_metadata("test_skill", "test input")

            assert result == {"data": "test"}
            assert "similarity" in metadata
            assert "timestamp" in metadata
        finally:
            Path(cache_path).unlink(missing_ok=True)

    def test_stats(self) -> None:
        """Test getting cache statistics."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            cache_path = tmp.name

        try:
            cache = SemanticCache(cache_path=cache_path)

            cache.add("skill_a", "input1", {"result": "a"})
            cache.add("skill_b", "input2", {"result": "b"})

            stats = cache.stats()

            assert stats["total_entries"] == 2
            assert "skill_a" in stats["skills"]
            assert "skill_b" in stats["skills"]
        finally:
            Path(cache_path).unlink(missing_ok=True)

    def test_clear_cache(self) -> None:
        """Test clearing all cache entries."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            cache_path = tmp.name

        try:
            cache = SemanticCache(cache_path=cache_path)

            cache.add("skill_a", "input1", {"result": "a"})
            cache.add("skill_b", "input2", {"result": "b"})

            cache.clear()

            stats = cache.stats()
            assert stats["total_entries"] == 0
        finally:
            Path(cache_path).unlink(missing_ok=True)

    def test_save_and_load(self) -> None:
        """Test saving and loading cache."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            cache_path = tmp.name

        try:
            # Create cache and add entries
            cache1 = SemanticCache(cache_path=cache_path)
            cache1.add("skill_a", "input1", {"result": "a"})
            cache1.add("skill_b", "input2", {"result": "b"})
            cache1.save()

            # Load cache
            cache2 = SemanticCache(cache_path=cache_path)

            assert len(cache2._entries) == 2
            assert cache2.get("skill_a", "input1") == {"result": "a"}
            assert cache2.get("skill_b", "input2") == {"result": "b"}
        finally:
            Path(cache_path).unlink(missing_ok=True)

    def test_different_skill_names(self) -> None:
        """Test that different skill names are cached separately."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            cache_path = tmp.name

        try:
            cache = SemanticCache(cache_path=cache_path)

            # Add entries with same input but different skills
            cache.add("skill_a", "same_input", {"result": "a"})
            cache.add("skill_b", "same_input", {"result": "b"})

            # Should get correct results for each skill
            assert cache.get("skill_a", "same_input") == {"result": "a"}
            assert cache.get("skill_b", "same_input") == {"result": "b"}
        finally:
            Path(cache_path).unlink(missing_ok=True)


class TestCacheThreshold:
    """Tests for cache threshold behavior."""

    def test_cache_threshold(self) -> None:
        """Test cache similarity threshold."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            cache_path = tmp.name

        try:
            # Create cache with low threshold
            cache = SemanticCache(cache_path=cache_path, threshold=0.5)

            cache.add(
                skill_name="test",
                input_text="very specific test input",
                result={"status": "found"}
            )

            # Search with very similar input
            result = cache.get(
                skill_name="test",
                input_text="very specific test input modified"
            )

            # Should find due to threshold
            assert result is not None
        finally:
            Path(cache_path).unlink(missing_ok=True)


class TestCacheSerialization:
    """Tests for cache serialization."""

    def test_complex_result_types(self) -> None:
        """Test caching complex result types."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            cache_path = tmp.name

        try:
            cache = SemanticCache(cache_path=cache_path)

            # Complex result types
            complex_result = {
                "data": [1, 2, 3],
                "nested": {"key": "value"},
                "status": "success"
            }

            cache.add("skill", "input", complex_result)
            retrieved = cache.get("skill", "input")

            assert retrieved == complex_result
        finally:
            Path(cache_path).unlink(missing_ok=True)


class TestSemanticCacheAPI:
    """Integration tests for API endpoints."""

    def test_create_client(self) -> None:
        """Test that we can create a client."""
        import importlib
        from skill_cache_layer import api

        # Verify module can be imported without errors
        assert hasattr(api, 'app')
        assert api.app is not None
