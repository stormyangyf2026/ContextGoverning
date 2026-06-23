"""Permission model — visibility, RBAC, entity boundaries for each context."""
from sqlalchemy import Column, String, ForeignKey, Index
from app.models._types import UUID, ARRAY
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, WorkspaceMixin, gen_uuid


class Permission(Base, TimestampMixin, WorkspaceMixin):
    __tablename__ = "permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    context_id = Column(UUID(as_uuid=True), ForeignKey("context_items.id", ondelete="CASCADE"), nullable=False)
    visibility = Column(String(16), nullable=False, default="internal")
    allowed_roles = Column(ARRAY(String), default=[])
    restricted_entity_type = Column(String(32), nullable=True)
    restricted_entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id"), nullable=True)

    context = relationship("ContextItem", back_populates="permissions")

    __table_args__ = (
        Index("idx_permissions_context", "context_id"),
        Index("idx_permissions_visibility", "visibility"),
    )
