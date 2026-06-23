"""User settings model (EAV schema)."""
from sqlalchemy import Column, String, ForeignKey, UniqueConstraint, Index
from app.models._types import UUID, JSONB
from app.models.base import Base, TimestampMixin, WorkspaceMixin, gen_uuid


class UserSetting(Base, TimestampMixin, WorkspaceMixin):
    __tablename__ = "user_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    section = Column(String(64), nullable=False)
    setting_key = Column(String(128), nullable=False)
    setting_value = Column(JSONB, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "section", "setting_key"),
        Index("idx_user_settings_user", "user_id"),
        Index("idx_user_settings_section", "section"),
    )
