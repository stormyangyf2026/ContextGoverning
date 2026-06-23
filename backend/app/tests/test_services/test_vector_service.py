"""Tests for VectorService — pgvector vector index operations."""
import pytest
import struct
from app.services.vector_service import get_vector_service


class TestVectorService:
    """Test vector serialization and search operations."""

    def test_build_vector_creates_bytes(self):
        """build_vector should convert float list to pgvector binary."""
        svc = get_vector_service()
        embedding = [0.1, 0.2, 0.3]
        result = svc.build_vector(embedding)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_build_and_parse_roundtrip(self):
        """build_vector + parse_vector should round-trip correctly."""
        svc = get_vector_service()
        original = [0.1, 0.2, 0.3, 0.4, 0.5]
        binary = svc.build_vector(original)
        parsed = svc.parse_vector(binary)

        assert len(parsed) == len(original)
        for a, b in zip(parsed, original):
            assert abs(a - b) < 0.02

    def test_search_similar_returns_empty_when_no_vectors(self, db):
        """search_similar should return empty list when no vectors exist."""
        svc = get_vector_service()
        results = svc.search_similar(db, [0.0] * 1024, top_k=10)
        assert isinstance(results, list)
        assert len(results) == 0

    def test_batch_index_noop_when_no_vector(self, db):
        """batch_index should handle None context gracefully."""
        svc = get_vector_service()
        svc.batch_index(db, "nonexistent_context_id", [0.0] * 1024)

    def test_singleton_pattern(self):
        """get_vector_service should return the same instance."""
        svc1 = get_vector_service()
        svc2 = get_vector_service()
        assert svc1 is svc2

    def test_build_vector_empty(self):
        """build_vector with empty list should produce bytes."""
        svc = get_vector_service()
        result = svc.build_vector([])
        assert isinstance(result, bytes)

    def test_parse_vector_none_binary(self):
        """parse_vector with None should return empty list."""
        svc = get_vector_service()
        result = svc.parse_vector(None)
        assert result == []

    def test_search_similar_with_min_similarity(self, db):
        """search_similar with min_similarity should work."""
        svc = get_vector_service()
        results = svc.search_similar(db, [0.0] * 1024, top_k=5, min_similarity=0.8)
        assert isinstance(results, list)
