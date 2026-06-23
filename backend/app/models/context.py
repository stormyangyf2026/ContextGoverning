"""Context items model — the core table of the platform."""
from sqlalchemy import (
    Column, String, Text, Float, Boolean, Integer, Date, DateTime, ForeignKey, Index,
)
from app.models._types import UUID, ARRAY, JSONB, Vector
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, SoftDeleteMixin, WorkspaceMixin, gen_uuid, utcnow


VALID_DOMAINS = ("customer", "project", "operations", "external")
VALID_LIFECYCLE_STATUSES = (
    "created", "pending_review", "active", "decaying",
    "needs_update", "superseded", "contradicted", "archived",
)
VALID_CONFIDENCE_LEVELS = ("L0", "L1", "L2", "L3", "L4", "L5")


class ContextItem(Base, TimestampMixin, SoftDeleteMixin, WorkspaceMixin):
    __tablename__ = "context_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    context_id = Column(String(64), unique=True, nullable=False, index=True)
    title = Column(String(512), nullable=False)
    content = Column(Text, nullable=False)
    content_vector = Column(Vector(1024), nullable=True)
    content_hash = Column(String(64), nullable=False)

    # Classification
    domain = Column(String(32), nullable=False)
    sub_category = Column(String(64), nullable=True)
    tags = Column(ARRAY(Text), default=[])

    # Confidence
    confidence_level = Column(String(4), nullable=False, default="L2")
    confidence_score = Column(Float, nullable=False, default=0.5)
    confidence_source = Column(Text, nullable=True)
    confidence_source_type = Column(String(32), nullable=True)
    confidence_extracted_by = Column(String(128), nullable=True)

    # Sub-type for special contexts (lesson_learned, etc.)
    context_subtype = Column(String(32), nullable=True)
    context_role = Column(String(16), nullable=True)
    structured_fields = Column(JSONB, nullable=True)

    # Lifecycle
    lifecycle_status = Column(String(16), nullable=False, default="pending_review")
    lifecycle_valid_from = Column(Date, nullable=True)
    lifecycle_valid_until = Column(Date, nullable=True)
    lifecycle_superseded_by = Column(UUID(as_uuid=True), ForeignKey("context_items.id"), nullable=True)

    # Immutability & versioning
    is_immutable = Column(Boolean, nullable=False, default=False)
    version = Column(Integer, nullable=False, default=1)
    superseded_by = Column(UUID(as_uuid=True), ForeignKey("context_items.id"), nullable=True)

    # Source tracking
    source_url = Column(Text, nullable=True)
    source_document_title = Column(String(512), nullable=True)
    source_system = Column(String(32), nullable=True)
    source_platform = Column(String(32), nullable=True)
    source_collected_at = Column(DateTime(timezone=True), nullable=True)

    # People
    created_by = Column(String(128), nullable=False)
    verified_by = Column(String(128), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)

    # Relevance
    relevance_score = Column(Float, default=0.0)

    # RLHF classification tracking
    classification_source = Column(String(16), default="rule")  # rule / learned / manual
    classification_rule_version = Column(String(32), nullable=True)
    last_classified_at = Column(DateTime(timezone=True), nullable=True)
    auto_classification_correct = Column(Boolean, nullable=True)

    # Relationships
    entities = relationship("ContextEntityMap", back_populates="context", cascade="all, delete-orphan")
    permissions = relationship("Permission", back_populates="context", uselist=False, cascade="all, delete-orphan")
    relations_source = relationship("Relation", foreign_keys="Relation.source_id", back_populates="source")
    relations_target = relationship("Relation", foreign_keys="Relation.target_id", back_populates="target")

    __table_args__ = (
        Index("idx_context_items_domain", domain),
        Index("idx_context_items_lifecycle_status", lifecycle_status),
        Index("idx_context_items_confidence", confidence_level),
        Index("idx_context_items_content_hash", content_hash),
        Index("idx_context_items_source_system", source_system),
        Index("idx_context_items_context_subtype", context_subtype),
        Index("idx_context_items_version", version),
        Index("idx_context_items_is_immutable", is_immutable, postgresql_where=is_immutable),
    )
