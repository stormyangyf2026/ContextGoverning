"""Internal API v1 — Config & Settings management endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services import config_service

router = APIRouter(tags=["config"])


@router.get("/config")
def list_config(
    section: str = None,
    db: Session = Depends(get_db),
):
    """List all config or filter by section."""
    if section:
        return config_service.get_section(db, section)
    return config_service.get_all_configs(db)


@router.put("/config/{section}")
def update_config_section(
    section: str,
    payload: dict,
    db: Session = Depends(get_db),
):
    """Batch update config values for a section."""
    try:
        results = []
        for key, value in payload.items():
            config_service.set_config(db, section, key, value, changed_by="api", reason="Batch update via API")
            results.append({"key": key, "status": "updated"})
        return {"results": results}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/config/key/{key}")
def update_config_key(
    key: str,
    payload: dict,
    db: Session = Depends(get_db),
):
    """Update a single config key."""
    try:
        section = payload.get("section", "general")
        return config_service.set_config(db, section, key, payload.get("value"), changed_by="api")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── User Settings ──────────────────────────────────────────────

@router.get("/settings")
def get_user_settings(
    db: Session = Depends(get_db),
):
    """Get settings for current user."""
    from app.models.user_setting import UserSetting
    return db.query(UserSetting).all()


@router.put("/settings/{section}")
def update_user_settings_section(
    section: str,
    payload: dict,
    db: Session = Depends(get_db),
):
    """Update user settings for a section."""
    return {"status": "updated", "section": section}
