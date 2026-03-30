"""Semantic cache implementation for skill-based agent reasoning."""

import hashlib
import json
import logging
import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Represents a cached skill execution result."""

    query_hash: str
    skill_name: str
    input_signature: str
    result: Any
    timestamp: float = field(default_factory=lambda: np.datetime64("now").astype(int) / 1e9)
    confidence: float = 1.0


class SemanticCache:
    """High-performance semantic cache for skill-based reasoning."""

    def __init__(
        self,
        cache_path: str | Path | None = None,
        dimension: int = 384,
        threshold: float = 0.85
    ):
        """Initialize the semantic cache.

        Args:
            cache_path: Path to cache storage file
            dimension: Dimension of the vector embedding space
            threshold: Similarity threshold for cache hits (0.0-1.0)
        """
        self.cache_path = Path(cache_path or ".skill_cache.pkl")
        self.dimension = dimension
        self.threshold = threshold

        # Vector storage
        self._embeddings: list[np.ndarray] = []
        self._entries: list[CacheEntry] = []

        # Load existing cache if available
        if self.cache_path.exists():
            self._load_cache()
            logger.info(f"Loaded cache with {len(self._entries)} entries from {self.cache_path}")

    def _create_query_signature(self, skill_name: str, input_text: str) -> str:
        """Create a deterministic signature for a query.

        Args:
            skill_name: Name of the skill being executed
            input_text: Input text to process

        Returns:
            Normalized signature string
        """
        # Normalize input
        normalized = input_text.lower().strip()
        normalized = " ".join(normalized.split())

        # Create hash-based signature
        combined = f"{skill_name}:{normalized}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    def _create_embedding(self, text: str) -> np.ndarray:
        """Create a simple embedding for text.

        In production, this would use a real embedding model.
        For now, we use a simple hash-based embedding.

        Args:
            text: Text to embed

        Returns:
            Vector embedding
        """
        # Create deterministic embedding from text hash
        hash_value = int(hashlib.sha256(text.encode()).hexdigest(), 16)

        # Generate dimension-length vector
        embedding = np.zeros(self.dimension, dtype=np.float32)
        np.random.seed(hash_value % (2**32))

        for i in range(self.dimension):
            embedding[i] = (hash_value % 1000) / 1000.0
            hash_value = hash_value >> 10

        return embedding

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Similarity score between 0.0 and 1.0
        """
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        dot_product = np.dot(vec1, vec2)
        return float(dot_product / (norm1 * norm2))

    def search(
        self,
        skill_name: str,
        input_text: str,
        return_embedding: bool = False
    ) -> CacheEntry | tuple[CacheEntry, float] | None:
        """Search for a similar cached entry.

        Args:
            skill_name: Name of the skill
            input_text: Input text to search for
            return_embedding: Whether to return embedding with result

        Returns:
            CacheEntry if found, or tuple of (entry, similarity) if return_embedding
        """
        query_embedding = self._create_embedding(f"{skill_name}:{input_text}")
        query_signature = self._create_query_signature(skill_name, input_text)

        best_match = None
        best_similarity = 0.0

        for i, entry in enumerate(self._entries):
            # Fast check: skip if signatures match exactly
            if entry.input_signature == query_signature:
                if best_match is None:
                    best_match = entry
                    best_similarity = 1.0
                continue

            # Calculate similarity
            similarity = self._cosine_similarity(
                self._embeddings[i],
                query_embedding
            )

            if similarity > best_similarity:
                best_match = entry
                best_similarity = similarity

        # Check if similarity meets threshold
        if best_match and best_similarity >= self.threshold:
            logger.info(
                f"Cache hit for {skill_name}: "
                f"similarity={best_similarity:.3f}"
            )
            if return_embedding:
                return best_match, best_similarity
            return best_match

        return None

    def add(
        self,
        skill_name: str,
        input_text: str,
        result: Any,
        confidence: float = 1.0
    ) -> CacheEntry:
        """Add a new entry to the cache.

        Args:
            skill_name: Name of the skill
            input_text: Input text
            result: Execution result
            confidence: Confidence score (0.0-1.0)

        Returns:
            CacheEntry for the new entry
        """
        signature = self._create_query_signature(skill_name, input_text)
        embedding = self._create_embedding(f"{skill_name}:{input_text}")

        entry = CacheEntry(
            query_hash=signature,
            skill_name=skill_name,
            input_signature=signature,
            result=result,
            confidence=confidence
        )

        self._embeddings.append(embedding)
        self._entries.append(entry)

        logger.info(f"Added cache entry: {skill_name}")

        return entry

    def get(self, skill_name: str, input_text: str) -> Any | None:
        """Get cached result for a query.

        Args:
            skill_name: Name of the skill
            input_text: Input text

        Returns:
            Cached result or None if not found
        """
        entry = self.search(skill_name, input_text)
        return entry.result if entry else None

    def get_with_metadata(
        self,
        skill_name: str,
        input_text: str
    ) -> tuple[Any, dict[str, Any]] | None:
        """Get cached result with metadata.

        Args:
            skill_name: Name of the skill
            input_text: Input text

        Returns:
            Tuple of (result, metadata) or None
        """
        result = self.search(skill_name, input_text)

        if result is None:
            return None

        metadata = {
            "similarity": result.confidence,
            "timestamp": result.timestamp,
            "skill_name": result.skill_name
        }

        return result.result, metadata

    def save(self) -> None:
        """Save cache to disk."""
        try:
            cache_data = {
                "version": "1.0",
                "entries": [
                    {
                        "query_hash": entry.query_hash,
                        "skill_name": entry.skill_name,
                        "input_signature": entry.input_signature,
                        "result": json.dumps(entry.result, default=str),
                        "timestamp": entry.timestamp,
                        "confidence": entry.confidence
                    }
                    for entry in self._entries
                ],
                "embeddings_shape": (len(self._embeddings), self.dimension)
            }

            with self.cache_path.open("w") as f:
                json.dump(cache_data, f)

            logger.info(f"Saved cache with {len(self._entries)} entries to {self.cache_path}")

        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
            raise

    def _load_cache(self) -> None:
        """Load cache from disk."""
        try:
            with self.cache_path.open("r") as f:
                cache_data = json.load(f)

            for entry_data in cache_data["entries"]:
                # Try to parse result as JSON first
                try:
                    result = json.loads(entry_data["result"])
                except (json.JSONDecodeError, TypeError):
                    try:
                        result = pickle.loads(entry_data["result"])
                    except (pickle.PickleError, TypeError):
                        result = entry_data["result"]

                entry = CacheEntry(
                    query_hash=entry_data["query_hash"],
                    skill_name=entry_data["skill_name"],
                    input_signature=entry_data["input_signature"],
                    result=result,
                    timestamp=entry_data["timestamp"],
                    confidence=entry_data["confidence"]
                )

                self._entries.append(entry)

                # Rebuild embeddings
                embedding = self._create_embedding(f"{entry.skill_name}:{entry.input_signature}")
                self._embeddings.append(embedding)

            logger.info(f"Loaded {len(self._entries)} cache entries")

        except Exception as e:
            logger.error(f"Failed to load cache: {e}")
            self._entries = []
            self._embeddings = []

    def clear(self) -> None:
        """Clear all cache entries."""
        self._entries = []
        self._embeddings = []
        logger.info("Cache cleared")

    def stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        return {
            "total_entries": len(self._entries),
            "cache_size_bytes": self.cache_path.stat().st_size if self.cache_path.exists() else 0,
            "embedding_dimension": self.dimension,
            "threshold": self.threshold,
            "skills": list(set(entry.skill_name for entry in self._entries))
        }
