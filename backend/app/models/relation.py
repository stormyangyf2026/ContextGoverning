"""Relation model — 7 relationship types between contexts."""
from sqlalchemy import Column, String, CheckConstraint, UniqueConstraint, Index, ForeignKey
from app.models._types import UUID, JSONB
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, WorkspaceMixin, gen_uuid

VALID_RELATION_TYPES = (
    "drives", "threatens", "depends_on", "contradicts",
    "supersedes", "informs", "part_of",
)


class Relation(Base, TimestampMixin, WorkspaceMixin):
    __tablename__ = "relations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    source_id = Column(UUID(as_uuid=True), ForeignKey("context_items.id", ondelete="CASCADE"), nullable=False)
    target_id = Column(UUID(as_uuid=True), ForeignKey("context_items.id", ondelete="CASCADE"), nullable=False)
    relation_type = Column(String(32), nullable=False)
    direction = Column(String(8), nullable=False, default="forward")
    extra_data = Column("metadata", JSONB, default={})
    created_by = Column(String(128), nullable=False)

    source = relationship("ContextItem", foreign_keys=[source_id], back_populates="relations_source")
    target = relationship("ContextItem", foreign_keys=[target_id], back_populates="relations_target")

    __table_args__ = (
        UniqueConstraint("source_id", "target_id", "relation_type"),
        CheckConstraint("source_id != target_id"),
        Index("idx_relations_source", "source_id"),
        Index("idx_relations_target", "target_id"),
        Index("idx_relations_type", "relation_type"),
    )
