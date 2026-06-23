"""Webhook delivery log model."""
from sqlalchemy import Column, String, Text, Integer, ForeignKey, Index
from app.models._types import UUID, JSONB
from app.models.base import Base, TimestampMixin, gen_uuid


class WebhookDeliveryLog(Base, TimestampMixin):
    __tablename__ = "webhook_delivery_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    event_id = Column(String(64), nullable=False)
    event_type = Column(String(64), nullable=False)
    target_url = Column(String(1024), nullable=False)
    request_body = Column(JSONB, nullable=True)
    response_status = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    attempt_number = Column(Integer, nullable=False, default=1)
    status = Column(String(16), nullable=False)
    error_message = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_webhook_logs_workspace", "workspace_id"),
        Index("idx_webhook_logs_event", "event_id"),
        Index("idx_webhook_logs_created", "created_at"),
    )
