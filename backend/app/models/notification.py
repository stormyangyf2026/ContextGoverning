"""Notification + notification_settings models."""
from sqlalchemy import Column, String, Text, Boolean, ForeignKey, Time, UniqueConstraint, Index
from app.models._types import UUID, ARRAY, JSONB
from app.models.base import Base, TimestampMixin, WorkspaceMixin, gen_uuid


class Notification(Base, TimestampMixin, WorkspaceMixin):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(32), nullable=False)
    title = Column(String(256), nullable=False)
    body = Column(Text, nullable=True)
    context_id = Column(UUID(as_uuid=True), ForeignKey("context_items.id", ondelete="SET NULL"), nullable=True)
    is_read = Column(Boolean, nullable=False, default=False)
    action_url = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_notifications_user", "user_id", "is_read"),
        Index("idx_notifications_created", "created_at"),
    )


class NotificationSetting(Base, TimestampMixin, WorkspaceMixin):
    __tablename__ = "notification_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    channels = Column(JSONB, nullable=False, default={"feishu_bot": True, "in_app": True, "email": False})
    quiet_hours_start = Column(Time, nullable=True)
    quiet_hours_end = Column(Time, nullable=True)
    enabled_types = Column(ARRAY(String), default=[])
