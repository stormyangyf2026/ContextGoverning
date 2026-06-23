"""Internal API v1 — Permissions management endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.permission_service import get_effective_filters
from app.models.permission import Permission

router = APIRouter(tags=["permissions"])


@router.get("/permissions/check")
def check_permission(
    user_id: str,
    context_id: str,
    db: Session = Depends(get_db),
):
    """Check if a user can access a context."""
    filters = get_effective_filters(db, user_id)
    return {"can_access": True, "filters": filters}


@router.put("/permissions/{context_id}")
def update_permission(
    context_id: str,
    payload: dict,
    db: Session = Depends(get_db),
):
    """Update permissions for a context."""
    perm = db.query(Permission).filter(Permission.context_id == context_id).first()
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")
    for key in payload:
        if hasattr(perm, key):
            setattr(perm, key, payload[key])
    db.commit()
    return perm
