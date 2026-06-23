"""Unit tests for the deduplication pipeline."""
import hashlib
import pytest
from unittest.mock import patch, MagicMock
from app.pipelines.dedup_pipeline import (
    content_hash, check_exact_duplicate, dedup_check, DEFAULT_SIMILARITY_THRESHOLD,
)


class TestContentHash:
    def test_hash_is_stable(self):
        h1 = content_hash("hello world")
        h2 = content_hash("hello world")
        assert h1 == h2

    def test_hash_is_deterministic(self):
        assert content_hash("test") == hashlib.sha256("test".encode("utf-8")).hexdigest()

    def test_different_content_different_hash(self):
        assert content_hash("abc") != content_hash("def")

    def test_empty_string_hash(self):
        h = content_hash("")
        assert len(h) == 64  # SHA256 hex digest length


class TestExactDedup:
    def test_no_duplicate_on_empty_db(self, db):
        result = check_exact_duplicate(db, "unique content")
        assert result is None

    def test_duplicate_detected(self, db, sample_context):
        result = check_exact_duplicate(db, "这是一个测试上下文的内容")
        assert result is not None
        assert result.context_id == "ctx_test_001"

    def test_different_content_no_match(self, db, sample_context):
        result = check_exact_duplicate(db, "completely different content")
        assert result is None


class TestDedupCheck:
    def test_new_content_passes(self, db):
        result = dedup_check(db, "brand new content never seen before")
        assert result is None

    def test_exact_duplicate_blocked(self, db, sample_context):
        result = dedup_check(db, "这是一个测试上下文的内容")
        assert result is not None

    def test_dedup_with_none_vector_skips_semantic(self, db):
        """When vector is None, only exact dedup runs."""
        result = dedup_check(db, "unique content", content_vector=None)
        assert result is None


class TestDefaultThreshold:
    def test_default_threshold_from_config(self):
        """DEFAULT_SIMILARITY_THRESHOLD should be a float between 0 and 1."""
        assert 0.0 < DEFAULT_SIMILARITY_THRESHOLD <= 1.0
