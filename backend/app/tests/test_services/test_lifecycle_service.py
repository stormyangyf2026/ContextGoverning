"""Unit tests for lifecycle state machine service."""
import pytest
from datetime import date, datetime, timezone
from unittest.mock import patch

from app.services.lifecycle_service import (
    STATE_TRANSITIONS, is_valid_transition, transition,
    auto_trigger_decay, auto_trigger_supersede,
)


class TestStateTransitions:
    def test_created_to_pending_review_is_valid(self):
        assert is_valid_transition("created", "pending_review") is True

    def test_created_to_archived_is_valid(self):
        assert is_valid_transition("created", "archived") is True

    def test_created_to_active_is_invalid(self):
        assert is_valid_transition("created", "active") is False

    def test_active_to_decaying_is_valid(self):
        assert is_valid_transition("active", "decaying") is True

    def test_active_to_needs_update_is_valid(self):
        assert is_valid_transition("active", "needs_update") is True

    def test_active_to_superseded_is_valid(self):
        assert is_valid_transition("active", "superseded") is True

    def test_active_to_contradicted_is_valid(self):
        assert is_valid_transition("active", "contradicted") is True

    def test_decaying_to_active_is_valid(self):
        assert is_valid_transition("decaying", "active") is True

    def test_decaying_to_needs_update_is_valid(self):
        assert is_valid_transition("decaying", "needs_update") is True

    def test_superseded_to_active_is_invalid(self):
        assert is_valid_transition("superseded", "active") is False

    def test_superseded_to_archived_is_valid(self):
        assert is_valid_transition("superseded", "archived") is True

    def test_archived_to_active_is_valid(self):
        """Archived can be restored to active."""
        assert is_valid_transition("archived", "active") is True

    def test_contradicted_to_active_is_valid(self):
        assert is_valid_transition("contradicted", "active") is True

    def test_invalid_current_state_returns_false(self):
        assert is_valid_transition("nonexistent", "active") is False

    def test_all_states_are_valid(self):
        """All 8 states should exist as keys."""
        expected = {"created", "pending_review", "active", "decaying",
                     "needs_update", "superseded", "contradicted", "archived"}
        assert set(STATE_TRANSITIONS.keys()) == expected


class TestTransition:
    def test_transition_created_to_pending_review(self, db, sample_context):
        sample_context.lifecycle_status = "created"
        db.commit()
        result = transition(db, "test_user", sample_context, "pending_review")
        assert result.lifecycle_status == "pending_review"

    def test_transition_active_to_archived(self, db, sample_context):
        sample_context.lifecycle_status = "active"
        db.commit()
        result = transition(db, "test_user", sample_context, "archived")
        assert result.lifecycle_status == "archived"
        assert result.archived_at is not None

    def test_transition_active_sets_immutability_for_l3(self, db, sample_context):
        """When activating L3+ context, immutability should be set."""
        sample_context.confidence_level = "L3"
        sample_context.lifecycle_status = "pending_review"
        db.commit()
        result = transition(db, "test_user", sample_context, "active")
        assert result.is_immutable is True
        assert result.lifecycle_valid_from is not None

    def test_transition_active_does_not_set_immutability_for_l2(self, db, sample_context):
        """L2 context activated should NOT become immutable."""
        sample_context.confidence_level = "L2"
        sample_context.lifecycle_status = "pending_review"
        sample_context.is_immutable = False
        db.commit()
        result = transition(db, "test_user", sample_context, "active")
        assert result.is_immutable is False

    def test_invalid_transition_raises(self, db, sample_context):
        sample_context.lifecycle_status = "created"
        db.commit()
        with pytest.raises(ValueError, match="Invalid transition"):
            transition(db, "test_user", sample_context, "active")


class TestAutoTriggerDecay:
    def test_decay_finds_nothing_for_recent_contexts(self, db, sample_context):
        sample_context.lifecycle_status = "active"
        db.commit()
        decayed = auto_trigger_decay(db)
        assert len(decayed) == 0
