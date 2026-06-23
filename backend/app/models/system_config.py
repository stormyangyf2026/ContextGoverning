"""System config model (EAV schema)."""
from sqlalchemy import Column, String, Text, Boolean, Integer, UniqueConstraint, Index
from app.models._types import UUID, JSONB
from app.models.base import Base, TimestampMixin, WorkspaceMixin, gen_uuid


class SystemConfig(Base, TimestampMixin, WorkspaceMixin):
    __tablename__ = "system_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    section = Column(String(64), nullable=False)
    config_key = Column(String(128), nullable=False)
    config_value = Column(JSONB, nullable=False)
    value_type = Column(String(16), nullable=False)
    description = Column(Text, nullable=True)
    default_value = Column(JSONB, nullable=False)
    validation = Column(JSONB, nullable=True)
    input_hint = Column(Text, nullable=True)
    impact_note = Column(Text, nullable=True)
    is_visible = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)
    updated_by = Column(String(128), nullable=True)

    __table_args__ = (
        UniqueConstraint("section", "config_key"),
        Index("idx_system_configs_section", "section"),
    )
