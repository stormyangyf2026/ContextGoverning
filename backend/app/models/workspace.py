"""Workspace model — multi-tenant support."""
from sqlalchemy import Column, String, Text, Index
from app.models._types import UUID, JSONB
from app.models.base import Base, TimestampMixin, gen_uuid


class Workspace(Base, TimestampMixin):
    __tablename__ = "workspaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    workspace_id = Column(String(32), unique=True, nullable=False)
    name = Column(String(256), nullable=False)
    slug = Column(String(128), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    auth_config = Column(JSONB, nullable=False, default={})
    features = Column(JSONB, nullable=False, default={})
    quotas = Column(JSONB, nullable=False, default={})
    webhook_config = Column(JSONB, nullable=True)
    ui_config = Column(JSONB, nullable=True)
    status = Column(String(16), nullable=False, default="active")

    __table_args__ = (
        Index("idx_workspaces_slug", "slug"),
        Index("idx_workspaces_status", "status"),
    )
