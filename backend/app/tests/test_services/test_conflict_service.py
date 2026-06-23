"""Unit tests for conflict detection service."""
import pytest
from app.services.conflict_service import detect_conflicts


class TestDetectConflicts:
    def test_detect_conflicts_with_nonexistent_context(self, db):
        """Should return empty list for nonexistent context."""
        conflicts = detect_conflicts(db, "nonexistent-context-id")
        assert conflicts == []

    def test_detect_conflicts_without_vector(self, db, sample_context):
        """Context without vector embedding returns empty."""
        sample_context.content_vector = None
        db.commit()
        conflicts = detect_conflicts(db, sample_context.context_id)
        assert conflicts == []
