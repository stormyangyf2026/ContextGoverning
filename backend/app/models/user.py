"""User model + user_entity_assignments."""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UniqueConstraint, Index
from app.models._types import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, WorkspaceMixin, gen_uuid

VALID_ROLES = ("admin", "partner", "senior_consultant", "consultant")


class User(Base, TimestampMixin, WorkspaceMixin):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    username = Column(String(128), unique=True, nullable=False)
    email = Column(String(256), unique=True, nullable=False)
    display_name = Column(String(256), nullable=True)
    hashed_password = Column(String(256), nullable=True)
    role = Column(String(32), nullable=False, default="consultant")
    avatar_url = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    entity_assignments = relationship("UserEntityAssignment", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (Index("idx_users_role", "role"),)


class UserEntityAssignment(Base, WorkspaceMixin):
    __tablename__ = "user_entity_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    entity_type = Column(String(32), nullable=False)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    access_level = Column(String(16), nullable=False, default="read")

    user = relationship("User", back_populates="entity_assignments")

    __table_args__ = (
        UniqueConstraint("user_id", "entity_type", "entity_id"),
        Index("idx_uea_user", "user_id"),
        Index("idx_uea_entity", "entity_id", "entity_type"),
    )
