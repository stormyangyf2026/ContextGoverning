"""JWT config model."""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from app.models._types import UUID, JSONB
from app.models.base import Base, TimestampMixin, gen_uuid


class JwtConfig(Base, TimestampMixin):
    __tablename__ = "jwt_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, unique=True)
    issuer = Column(String(512), nullable=False)
    jwks_url = Column(String(1024), nullable=True)
    audience = Column(String(256), nullable=True)
    claim_mapping = Column(JSONB, nullable=False, default={})
    default_role = Column(String(32), nullable=False, default="consultant")
    token_refresh_url = Column(String(1024), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    last_verified_at = Column(DateTime(timezone=True), nullable=True)
