"""Config change log model."""
from sqlalchemy import Column, String, Text, Index
from app.models._types import UUID, JSONB
from app.models.base import Base, TimestampMixin, WorkspaceMixin, gen_uuid


class ConfigChangeLog(Base, TimestampMixin, WorkspaceMixin):
    __tablename__ = "config_change_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    config_type = Column(String(16), nullable=False)
    section = Column(String(64), nullable=False)
    config_key = Column(String(128), nullable=False)
    old_value = Column(JSONB, nullable=True)
    new_value = Column(JSONB, nullable=False)
    changed_by = Column(String(128), nullable=False)
    change_reason = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_config_logs_type", "config_type"),
        Index("idx_config_logs_section", "section"),
        Index("idx_config_logs_created", "created_at"),
    )
