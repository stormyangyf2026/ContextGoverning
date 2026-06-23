"""Audit log model."""
from sqlalchemy import Column, String, ForeignKey, Index
from app.models._types import UUID, INET, JSONB
from app.models.base import Base, TimestampMixin, WorkspaceMixin, gen_uuid


class AuditLog(Base, TimestampMixin, WorkspaceMixin):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    context_id = Column(UUID(as_uuid=True), ForeignKey("context_items.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(32), nullable=False)
    actor = Column(String(128), nullable=False)
    changes = Column(JSONB, default={})
    ip_address = Column(INET, nullable=True)
    user_agent = Column(String, nullable=True)

    __table_args__ = (
        Index("idx_audit_context", "context_id"),
        Index("idx_audit_actor", "actor"),
        Index("idx_audit_action", "action"),
        Index("idx_audit_created", "created_at"),
    )
