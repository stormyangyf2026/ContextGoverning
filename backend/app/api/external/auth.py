"""External API — Authentication endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.api_key_auth import get_api_key_auth

router = APIRouter(tags=["external-auth"])


@router.post("/auth/verify-api-key")
def verify_api_key(payload: dict, db: Session = Depends(get_db)):
    """Verify an API key and return workspace info."""
    svc = get_api_key_auth()
    result = svc.verify_api_key(db, payload.get("api_key", ""))
    if not result:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return {"workspace_id": result, "status": "valid"}


@router.get("/auth/whoami")
def whoami(db: Session = Depends(get_db)):
    """Return current authenticated user info."""
    return {"user": "authenticated", "method": "api_key"}


@router.post("/auth/api-keys")
def create_api_key(payload: dict, db: Session = Depends(get_db)):
    """Generate a new API key."""
    svc = get_api_key_auth()
    return svc.generate_api_key(
        db, payload["workspace_id"], payload.get("name", "default")
    )


@router.get("/auth/api-keys")
def list_api_keys(workspace_id: str, db: Session = Depends(get_db)):
    """List API keys for a workspace."""
    svc = get_api_key_auth()
    return svc.list_api_keys(db, workspace_id)


@router.delete("/auth/api-keys/{key_id}")
def revoke_api_key(key_id: str, db: Session = Depends(get_db)):
    """Revoke an API key."""
    svc = get_api_key_auth()
    if not svc.revoke_api_key(db, key_id):
        raise HTTPException(status_code=404, detail="API key not found")
    return {"status": "revoked"}
