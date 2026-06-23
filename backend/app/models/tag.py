"""Context tag model."""
from sqlalchemy import Column, String, ForeignKey, UniqueConstraint, Index
from app.models._types import UUID
from app.models.base import Base, TimestampMixin, WorkspaceMixin, gen_uuid


class ContextTag(Base, TimestampMixin, WorkspaceMixin):
    __tablename__ = "context_tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    context_id = Column(UUID(as_uuid=True), ForeignKey("context_items.id", ondelete="CASCADE"), nullable=False)
    tag = Column(String(128), nullable=False)
    tag_type = Column(String(32), default="manual")

    __table_args__ = (
        UniqueConstraint("context_id", "tag"),
        Index("idx_tags_context", "context_id"),
        Index("idx_tags_tag", "tag"),
    )
