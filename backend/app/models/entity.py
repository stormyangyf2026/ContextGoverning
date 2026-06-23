"""Entity model."""
from sqlalchemy import Column, String, Text, UniqueConstraint, Index
from app.models._types import UUID, ARRAY, JSONB
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, WorkspaceMixin, gen_uuid


class Entity(Base, TimestampMixin, WorkspaceMixin):
    __tablename__ = "entities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    name = Column(String(256), nullable=False)
    type = Column(String(32), nullable=False)
    domain = Column(String(32), nullable=True)
    aliases = Column(ARRAY(Text), default=[])
    extra_data = Column("metadata", JSONB, default={})

    context_maps = relationship("ContextEntityMap", back_populates="entity")

    __table_args__ = (
        UniqueConstraint("name", "type"),
        Index("idx_entities_type", type),
        Index("idx_entities_domain", domain),
    )
