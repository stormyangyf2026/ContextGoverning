"""Context service — core CRUD + immutability enforcement + version management."""
from typing import Optional, List
from datetime import datetime, timezone
import hashlib

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.context import ContextItem, VALID_LIFECYCLE_STATUSES
from app.models.entity import Entity
from app.models.context_entity import ContextEntityMap
from app.models.audit import AuditLog as AuditLogModel
from app.core.audit import log_audit, log_lifecycle_change


def create_context(
    db: Session,
    actor: str,
    title: str,
    content: str,
    domain: str,
    context_id: str,
    source_system: Optional[str] = None,
    confidence_level: str = "L2",
    confidence_score: float = 0.5,
    confidence_source_type: Optional[str] = None,
    context_subtype: Optional[str] = None,
    context_role: Optional[str] = None,
    structured_fields: Optional[dict] = None,
) -> ContextItem:
    """Create a new context item."""
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    ctx = ContextItem(
        context_id=context_id,
        title=title,
        content=content,
        content_hash=content_hash,
        domain=domain,
        confidence_level=confidence_level,
        confidence_score=confidence_score,
        confidence_source_type=confidence_source_type,
        context_subtype=context_subtype,
        context_role=context_role,
        structured_fields=structured_fields,
        lifecycle_status="pending_review",
        source_system=source_system,
        created_by=actor,
        version=1,
        is_immutable=False,
    )
    db.add(ctx)
    db.commit()
    db.refresh(ctx)

    log_audit(db, "create", actor, ctx.id)
    return ctx


def get_context(db: Session, context_id: str) -> Optional[ContextItem]:
    """Get a context by its context_id (human-readable ID)."""
    return db.query(ContextItem).filter(ContextItem.context_id == context_id).first()


def get_context_by_id(db: Session, id: str) -> Optional[ContextItem]:
    """Get a context by its database UUID."""
    return db.query(ContextItem).filter(ContextItem.id == id).first()


def list_contexts(
    db: Session,
    domain: Optional[str] = None,
    lifecycle_status: Optional[str] = None,
    confidence_level: Optional[str] = None,
    source_system: Optional[str] = None,
    context_subtype: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
) -> List[ContextItem]:
    """List contexts with optional filters."""
    query = db.query(ContextItem).filter(ContextItem.is_deleted == False)
    if domain:
        query = query.filter(ContextItem.domain == domain)
    if lifecycle_status:
        query = query.filter(ContextItem.lifecycle_status == lifecycle_status)
    if confidence_level:
        query = query.filter(ContextItem.confidence_level == confidence_level)
    if source_system:
        query = query.filter(ContextItem.source_system == source_system)
    if context_subtype:
        query = query.filter(ContextItem.context_subtype == context_subtype)
    return query.order_by(ContextItem.created_at.desc()).offset(skip).limit(limit).all()


def update_context(
    db: Session,
    actor: str,
    context_id: str,
    title: Optional[str] = None,
    content: Optional[str] = None,
    domain: Optional[str] = None,
    sub_category: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> ContextItem:
    """Update context fields. Blocks update if context is immutable."""
    ctx = db.query(ContextItem).filter(ContextItem.context_id == context_id).first()
    if ctx is None:
        raise ValueError(f"Context not found: {context_id}")

    # Immutability check
    if ctx.is_immutable:
        raise ValueError(
            f"Context {context_id} is immutable. Create a new version instead."
        )

    changes = {}
    if title is not None and title != ctx.title:
        changes["title"] = {"old": ctx.title, "new": title}
        ctx.title = title
    if content is not None and content != ctx.content:
        changes["content"] = {"old_hash": ctx.content_hash, "new": "updated"}
        ctx.content = content
        ctx.content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    if domain is not None:
        changes["domain"] = {"old": ctx.domain, "new": domain}
        ctx.domain = domain
    if sub_category is not None:
        changes["sub_category"] = {"old": ctx.sub_category, "new": sub_category}
        ctx.sub_category = sub_category
    if tags is not None:
        changes["tags"] = {"old": ctx.tags, "new": tags}
        ctx.tags = tags

    if changes:
        db.commit()
        db.refresh(ctx)
        log_audit(db, "update", actor, ctx.id, changes)

    return ctx


def create_new_version(
    db: Session,
    actor: str,
    context_id: str,
    new_content: str,
    new_title: Optional[str] = None,
) -> ContextItem:
    """Create a new version of an immutable context.

    Old version is marked as superseded; new version starts as pending_review.
    """
    old_ctx = db.query(ContextItem).filter(ContextItem.context_id == context_id).first()
    if old_ctx is None:
        raise ValueError(f"Context not found: {context_id}")

    new_version = old_ctx.version + 1
    new_context_id = f"{context_id}_v{new_version}"

    # Create new version
    new_ctx = create_context(
        db=db,
        actor=actor,
        title=new_title or old_ctx.title,
        content=new_content,
        domain=old_ctx.domain,
        context_id=new_context_id,
        source_system=old_ctx.source_system,
        confidence_level=old_ctx.confidence_level,
        confidence_score=old_ctx.confidence_score,
        confidence_source_type=old_ctx.confidence_source_type,
        context_subtype=old_ctx.context_subtype,
        context_role=old_ctx.context_role,
    )
    new_ctx.version = new_version
    new_ctx.is_immutable = old_ctx.is_immutable

    # Supersede old version
    old_ctx.lifecycle_status = "superseded"
    old_ctx.superseded_by = new_ctx.id

    db.commit()
    db.refresh(new_ctx)

    log_lifecycle_change(
        db, actor, old_ctx.id,
        old_status="active", new_status="superseded",
        trigger=f"new_version_created:{new_context_id}",
    )

    return new_ctx


def update_lifecycle_status(
    db: Session,
    actor: str,
    context_id: str,
    new_status: str,
) -> ContextItem:
    """Update lifecycle status with audit log."""
    if new_status not in VALID_LIFECYCLE_STATUSES:
        raise ValueError(f"Invalid lifecycle status: {new_status}")

    ctx = db.query(ContextItem).filter(ContextItem.context_id == context_id).first()
    if ctx is None:
        raise ValueError(f"Context not found: {context_id}")

    old_status = ctx.lifecycle_status
    ctx.lifecycle_status = new_status

    # If activating after review, set immutability for L3+
    if new_status == "active" and ctx.confidence_level in ("L3", "L4", "L5"):
        ctx.is_immutable = True
        ctx.verified_by = actor
        ctx.verified_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(ctx)

    log_lifecycle_change(db, actor, ctx.id, old_status, new_status)
    return ctx


def soft_delete_context(
    db: Session,
    actor: str,
    context_id: str,
) -> ContextItem:
    """Soft delete a context item."""
    ctx = db.query(ContextItem).filter(ContextItem.context_id == context_id).first()
    if ctx is None:
        raise ValueError(f"Context not found: {context_id}")

    ctx.is_deleted = True
    ctx.deleted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ctx)

    log_audit(db, "delete", actor, ctx.id)
    return ctx
