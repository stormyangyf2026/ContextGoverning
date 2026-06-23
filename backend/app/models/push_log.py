"""Push log model."""
from sqlalchemy import Column, String, Text, ForeignKey, Index
from app.models._types import UUID, JSONB
from app.models.base import Base, TimestampMixin, WorkspaceMixin, gen_uuid


class PushLog(Base, TimestampMixin, WorkspaceMixin):
    __tablename__ = "push_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    rule_id = Column(UUID(as_uuid=True), ForeignKey("push_rules.id"), nullable=True)
    context_id = Column(UUID(as_uuid=True), ForeignKey("context_items.id"), nullable=True)
    triggered_by = Column(Text, nullable=False)
    target_user = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    target_channel = Column(String(32), nullable=False)
    status = Column(String(16), nullable=False, default="sent")
    message_content = Column(JSONB, nullable=True)

    __table_args__ = (
        Index("idx_push_logs_rule", "rule_id"),
        Index("idx_push_logs_user", "target_user"),
        Index("idx_push_logs_created", "created_at"),
    )
