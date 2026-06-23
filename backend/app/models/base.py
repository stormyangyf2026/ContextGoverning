"""Base model with shared columns and utilities."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Boolean, String
from app.models._types import UUID
from sqlalchemy.orm import DeclarativeBase, declared_attr


class Base(DeclarativeBase):
    pass


def gen_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    """Adds created_at/updated_at columns."""
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class SoftDeleteMixin:
    """Adds soft-delete columns."""
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class WorkspaceMixin:
    """Adds workspace_id for multi-tenant isolation."""
    workspace_id = Column(UUID(as_uuid=True), nullable=True, index=True)
