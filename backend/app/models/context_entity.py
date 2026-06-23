"""Context-entity junction table."""
from sqlalchemy import Column, String, ForeignKey, UniqueConstraint, Index
from app.models._types import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, gen_uuid


class ContextEntityMap(Base):
    __tablename__ = "context_entities_map"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    context_id = Column(UUID(as_uuid=True), ForeignKey("context_items.id", ondelete="CASCADE"), nullable=False)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(32), nullable=True)

    context = relationship("ContextItem", back_populates="entities")
    entity = relationship("Entity", back_populates="context_maps")

    __table_args__ = (
        UniqueConstraint("context_id", "entity_id"),
        Index("idx_cem_context", "context_id"),
        Index("idx_cem_entity", "entity_id"),
    )
