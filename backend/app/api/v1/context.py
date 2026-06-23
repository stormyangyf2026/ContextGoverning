"""Internal API v1 — Context management endpoints."""
from typing import Optional, List
import uuid as uuid_lib
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.context_service import (
    get_context, list_contexts, create_context as svc_create_context,
    update_context as svc_update_context,
)

router = APIRouter(tags=["contexts"])


def _model_to_dict(ctx):
    """Convert SQLAlchemy model to dict for JSON serialization."""
    return {
        "id": str(ctx.id),
        "context_id": ctx.context_id,
        "title": ctx.title,
        "content": ctx.content,
        "domain": ctx.domain,
        "confidence_level": ctx.confidence_level,
        "confidence_score": ctx.confidence_score,
        "confidence_source_type": ctx.confidence_source_type,
        "lifecycle_status": ctx.lifecycle_status,
        "created_by": ctx.created_by,
        "version": ctx.version,
        "is_immutable": ctx.is_immutable,
        "created_at": ctx.created_at.isoformat() if ctx.created_at else None,
        "updated_at": ctx.updated_at.isoformat() if getattr(ctx, "updated_at", None) else None,
        "source_system": ctx.source_system,
        "tags": ctx.tags or [],
        "sub_category": ctx.sub_category,
    }


def _list_to_dict(contexts):
    return [_model_to_dict(c) for c in contexts]


@router.get("/contexts")
def list_contexts_api(
    domain: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    confidence_min: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List all contexts with optional filters."""
    ctxs = list_contexts(db, domain=domain, lifecycle_status=status,
                         confidence_level=confidence_min,
                         skip=skip, limit=limit)
    return _list_to_dict(ctxs)


@router.get("/contexts/{context_id}")
def get_context_api(
    context_id: str,
    db: Session = Depends(get_db),
):
    """Get a single context by context_id."""
    ctx = get_context(db, context_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="Context not found")
    return _model_to_dict(ctx)


@router.post("/contexts")
def create_context_api(
    payload: dict,
    db: Session = Depends(get_db),
):
    """Create a new context entry."""
    try:
        cid = payload.get("context_id", f"ctx_{uuid_lib.uuid4().hex[:12]}")
        ctx = svc_create_context(
            db,
            actor=payload.get("created_by", "api"),
            title=payload["title"],
            content=payload["content"],
            domain=payload.get("domain", "operations"),
            context_id=cid,
            confidence_level=payload.get("confidence_level", "L2"),
            confidence_score=payload.get("confidence_score", 0.5),
            confidence_source_type=payload.get("confidence_source_type"),
            context_subtype=payload.get("context_subtype"),
            context_role=payload.get("context_role"),
            structured_fields=payload.get("structured_fields"),
        )
        return _model_to_dict(ctx)
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/contexts/{context_id}")
def update_context_api(
    context_id: str,
    payload: dict,
    db: Session = Depends(get_db),
):
    """Update a context entry."""
    try:
        ctx = svc_update_context(
            db,
            actor=payload.get("created_by", "api"),
            context_id=context_id,
            title=payload.get("title"),
            content=payload.get("content"),
            domain=payload.get("domain"),
            sub_category=payload.get("sub_category"),
            tags=payload.get("tags"),
        )
        return _model_to_dict(ctx)
    except ValueError as e:
        raise HTTPException(status_code=404 if "not found" in str(e).lower() else 400, detail=str(e))


@router.patch("/contexts/{context_id}/status")
def update_context_status_api(
    context_id: str,
    payload: dict,
    db: Session = Depends(get_db),
):
    """Update context lifecycle status."""
    ctx = get_context(db, context_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="Context not found")
    try:
        from app.services.lifecycle_service import transition
        new_status = payload.get("new_status", "")
        result = transition(db, actor=payload.get("actor", "api"), context=ctx, new_status=new_status)
        return _model_to_dict(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/contexts/{context_id}/confidence")
def update_context_confidence_api(
    context_id: str,
    payload: dict,
    db: Session = Depends(get_db),
):
    """Update context confidence manually (admin override)."""
    ctx = get_context(db, context_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="Context not found")
    if "level" in payload:
        ctx.confidence_level = payload["level"]
    if "score" in payload:
        ctx.confidence_score = payload["score"]
    if "source_type" in payload:
        ctx.confidence_source_type = payload["source_type"]
    db.commit()
    return ctx


@router.delete("/contexts/{context_id}")
def delete_context_api(
    context_id: str,
    db: Session = Depends(get_db),
):
    """Soft-delete a context."""
    ctx = get_context(db, context_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="Context not found")
    ctx.is_deleted = True
    db.commit()
    return {"status": "deleted"}
