"""Tests for RLHF feedback service."""
import pytest
from app.services.feedback_service import (
    submit_review_feedback, submit_classification_label,
    get_feedback_stats, get_reviewer_profile,
    calculate_reviewer_weight, build_training_dataset,
    detect_feedback_anomalies, mark_golden_sample,
)


class TestFeedbackService:
    """Test feedback collection and aggregation."""

    def test_submit_review_feedback_approved(self, db_session, sample_contexts, admin_user):
        """Submit a review with approved decision."""
        ctx = sample_contexts[0]
        record = submit_review_feedback(
            db=db_session,
            reviewer_id=str(admin_user.id),
            context_id=str(ctx.id),
            decision="approved",
            confidence_rating=4,
            quality_score=4,
        )
        assert record is not None
        assert record.decision == "approved"
        assert record.confidence_rating == 4

    def test_submit_review_feedback_with_correction(self, db_session, sample_contexts, admin_user):
        """Submit a review with classification correction."""
        ctx = sample_contexts[0]
        record = submit_review_feedback(
            db=db_session,
            reviewer_id=str(admin_user.id),
            context_id=str(ctx.id),
            decision="approved",
            original_domain=ctx.domain,
            corrected_domain="project",
            confidence_rating=3,
            quality_score=3,
        )
        assert record is not None
        assert record.corrected_domain == "project"
        assert record.classification_correct is False

    def test_submit_review_feedback_rejected(self, db_session, sample_contexts, admin_user):
        """Submit a rejected review."""
        ctx = sample_contexts[0]
        record = submit_review_feedback(
            db=db_session,
            reviewer_id=str(admin_user.id),
            context_id=str(ctx.id),
            decision="rejected",
            reject_reason="low_quality",
            review_comment="Content too vague",
        )
        assert record.decision == "rejected"
        assert record.reject_reason == "low_quality"

    def test_submit_classification_label(self, db_session, sample_contexts, admin_user):
        """Submit a classification correction label."""
        ctx = sample_contexts[0]
        label = submit_classification_label(
            db=db_session,
            labeler_id=str(admin_user.id),
            context_id=str(ctx.id),
            label_type="domain",
            predicted_value="customer",
            corrected_value="project",
            confidence=0.9,
        )
        assert label is not None
        assert label.corrected_value == "project"
        assert label.confidence == 0.9

    def test_get_feedback_stats(self, db_session, sample_contexts, admin_user):
        """Get feedback statistics after submitting reviews."""
        ctx = sample_contexts[0]
        submit_review_feedback(
            db=db_session, reviewer_id=str(admin_user.id),
            context_id=str(ctx.id), decision="approved",
            confidence_rating=4, quality_score=4,
        )
        stats = get_feedback_stats(db_session)
        assert stats["total_reviews"] >= 1
        assert stats["approved"] >= 1

    def test_get_reviewer_profile(self, db_session, sample_contexts, admin_user):
        """Get reviewer profile after submitting reviews."""
        ctx = sample_contexts[0]
        submit_review_feedback(
            db=db_session, reviewer_id=str(admin_user.id),
            context_id=str(ctx.id), decision="approved",
        )
        profile = get_reviewer_profile(db_session, str(admin_user.id))
        assert profile is not None
        assert profile["total_reviews"] >= 1

    def test_calculate_reviewer_weight(self, db_session, sample_contexts, admin_user):
        """Calculate reviewer weight."""
        ctx = sample_contexts[0]
        submit_review_feedback(
            db=db_session, reviewer_id=str(admin_user.id),
            context_id=str(ctx.id), decision="approved",
        )
        weight = calculate_reviewer_weight(
            db_session, str(admin_user.id),
            golden_accuracy=0.9, agreement_rate=0.85, total_reviews=50,
        )
        assert 0.1 <= weight <= 1.0

    def test_detect_feedback_anomalies_empty(self, db_session):
        """Detect anomalies with no data should return empty list."""
        anomalies = detect_feedback_anomalies(db_session)
        assert isinstance(anomalies, list)


class TestGoldenSamples:
    """Test golden sample management."""

    def test_mark_golden_sample(self, db_session, sample_contexts, admin_user):
        """Mark a review as golden sample."""
        ctx = sample_contexts[0]
        record = submit_review_feedback(
            db=db_session, reviewer_id=str(admin_user.id),
            context_id=str(ctx.id), decision="approved",
        )
        golden = mark_golden_sample(db_session, str(ctx.id), str(admin_user.id))
        assert golden.is_golden_sample is True
