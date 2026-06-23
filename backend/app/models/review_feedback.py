"""RLHF data models — review records, classification labels, rule weights, datasets, reviewer profiles, learning logs."""
import uuid
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.models._types import UUID
from app.models.base import Base, TimestampMixin, WorkspaceMixin


def gen_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── ReviewRecord ────────────────────────────────────────────────

class ReviewRecord(Base, TimestampMixin, WorkspaceMixin):
    """Structured review record capturing detailed reviewer feedback."""
    __tablename__ = "review_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    context_id = Column(UUID(as_uuid=True), ForeignKey("context_items.id", ondelete="CASCADE"), nullable=False)
    reviewer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Decision
    decision = Column(String(16), nullable=False)  # approved / rejected / needs_revision
    reject_reason = Column(String(32))  # incorrect_classification / outdated / low_quality / duplicate / irrelevant / other

    # Classification correction
    corrected_domain = Column(String(32))
    corrected_sub_category = Column(String(64))
    original_domain = Column(String(32))
    original_sub_category = Column(String(64))
    classification_correct = Column(Boolean)

    # Confidence rating (1-5 stars)
    confidence_rating = Column(Integer)
    confidence_adjustment = Column(String(8))  # upgrade / downgrade / confirm / none
    adjusted_confidence_level = Column(String(4))
    adjusted_confidence_score = Column(Float)

    # Quality assessment
    quality_score = Column(Integer)  # 1-5
    quality_dimensions = Column(Text)  # JSON: {clarity, accuracy, completeness, relevance, timeliness}

    # Golden sample
    is_golden_sample = Column(Boolean, default=False)

    # Metadata
    review_comment = Column(Text)
    review_duration_seconds = Column(Integer)
    review_source = Column(String(16), default="web")  # web / api / batch
    priority = Column(String(8), default="normal")  # high / normal / low


# ── ClassificationLabel ────────────────────────────────────────

class ClassificationLabel(Base, WorkspaceMixin):
    """Training labels for classification from reviewer corrections."""
    __tablename__ = "classification_labels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    context_id = Column(UUID(as_uuid=True), ForeignKey("context_items.id", ondelete="CASCADE"), nullable=False)
    labeler_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    label_type = Column(String(16), nullable=False)  # domain / sub_category / tag
    predicted_value = Column(String(64))
    corrected_value = Column(String(64), nullable=False)
    confidence = Column(Float, default=1.0)  # labeler's confidence in this label 0-1

    label_source = Column(String(16), default="review")  # review / user_feedback / admin_override / batch_import
    is_validated = Column(Boolean, default=False)
    validated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    validation_note = Column(Text)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


# ── ClassificationRuleWeight ───────────────────────────────────

class ClassificationRuleWeight(Base, WorkspaceMixin):
    """Weighted classification rule learned from human feedback."""
    __tablename__ = "classification_rule_weights"
    __table_args__ = (
        UniqueConstraint("workspace_id", "rule_keyword", "target_domain", name="uq_rule_keyword_domain_ws"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    rule_keyword = Column(String(128), nullable=False)
    target_domain = Column(String(32), nullable=False)
    target_sub_category = Column(String(64))

    weight = Column(Float, default=0.5)  # 0-1
    precision = Column(Float)
    recall_impact = Column(Float)

    total_matches = Column(Integer, default=0)
    correct_matches = Column(Integer, default=0)
    last_corrected = Column(DateTime(timezone=True))

    status = Column(String(16), default="active")  # active / deprecated / under_review
    source = Column(String(16), default="manual")  # manual / learned / imported
    learned_from = Column(Integer)  # number of feedback samples learned from

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


# ── FeedbackDataset ────────────────────────────────────────────

class FeedbackDataset(Base, WorkspaceMixin):
    """Training/validation/test dataset snapshot built from feedback data."""
    __tablename__ = "feedback_datasets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name = Column(String(256), nullable=False)
    description = Column(Text)
    dataset_type = Column(String(16), nullable=False)  # training / validation / test
    version = Column(String(32), nullable=False)

    total_samples = Column(Integer, default=0)
    domain_distribution = Column(Text)  # JSON
    class_accuracy_before = Column(Float)
    class_accuracy_after = Column(Float)

    status = Column(String(16), default="draft")  # draft / ready / training / completed / archived
    used_in_learning = Column(Boolean, default=False)

    snapshot_period_start = Column(DateTime(timezone=True))
    snapshot_period_end = Column(DateTime(timezone=True))
    min_confidence_label = Column(Float, default=0.7)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))


# ── ReviewerProfile ────────────────────────────────────────────

class ReviewerProfile(Base, WorkspaceMixin):
    """Reviewer performance profile for weighted voting and task assignment."""
    __tablename__ = "reviewer_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)

    total_reviews = Column(Integer, default=0)
    approved_count = Column(Integer, default=0)
    rejected_count = Column(Integer, default=0)
    needs_revision_count = Column(Integer, default=0)

    classification_accuracy = Column(Float)
    avg_confidence_variance = Column(Float)
    avg_review_duration = Column(Float)
    agreement_rate = Column(Float)
    golden_sample_accuracy = Column(Float)

    domain_expertise = Column(Text)  # JSON: {"customer": 0.9, "project": 0.7, ...}

    reviewer_level = Column(String(16), default="junior")  # junior / senior / expert
    reviewer_weight = Column(Float, default=0.5)  # 0-1
    is_active = Column(Boolean, default=True)

    last_review_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


# ── RuleLearningLog ────────────────────────────────────────────

class RuleLearningLog(Base, WorkspaceMixin):
    """Audit log for each rule learning execution."""
    __tablename__ = "rule_learning_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    dataset_id = Column(UUID(as_uuid=True), ForeignKey("feedback_datasets.id"))
    trigger_source = Column(String(32), nullable=False)  # manual / scheduled / threshold

    total_rules_before = Column(Integer)
    accuracy_before = Column(Float)

    rules_added = Column(Integer, default=0)
    rules_updated = Column(Integer, default=0)
    rules_deprecated = Column(Integer, default=0)
    accuracy_after = Column(Float)
    accuracy_improvement = Column(Float)

    learning_details = Column(Text)  # JSON: per-rule change details
    top_new_keywords = Column(Text)  # JSON: top discovered keywords

    status = Column(String(16), default="running")  # running / completed / failed / rolled_back
    error_message = Column(Text)
    duration_seconds = Column(Integer)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
