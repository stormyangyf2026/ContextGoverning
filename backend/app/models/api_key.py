"""API Key model."""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Index
from app.models._types import UUID, ARRAY
from app.models.base import Base, TimestampMixin, gen_uuid, utcnow


class ApiKey(Base, TimestampMixin):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(256), nullable=False)
    key_hash = Column(String(128), nullable=False)
    key_prefix = Column(String(8), nullable=False)
    role = Column(String(32), nullable=False, default="admin")
    entity_scope = Column(ARRAY(String), default=[])
    allowed_ips = Column(ARRAY(String), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_revoked = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("idx_api_keys_workspace", "workspace_id"),
        Index("idx_api_keys_key_hash", "key_hash"),
    )
