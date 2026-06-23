"""Push rule model."""
from sqlalchemy import Column, String, Text, Boolean, ForeignKey
from app.models._types import UUID, ARRAY, JSONB
from app.models.base import Base, TimestampMixin, WorkspaceMixin, gen_uuid


class PushRule(Base, TimestampMixin, WorkspaceMixin):
    __tablename__ = "push_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    name = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    trigger_type = Column(String(32), nullable=False)
    trigger_config = Column(JSONB, nullable=False, default={})
    target_roles = Column(ARRAY(String), nullable=False)
    target_users = Column(ARRAY(UUID(as_uuid=True)), default=[])
    template_id = Column(String(64), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
