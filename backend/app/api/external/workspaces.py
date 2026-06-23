"""External API — Workspace management endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.workspace_service import get_workspace_service

router = APIRouter(tags=["external-workspaces"])


@router.get("/workspaces")
def list_workspaces(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    svc = get_workspace_service()
    return svc.list_workspaces(db, skip=skip, limit=limit)


@router.post("/workspaces")
def create_workspace(payload: dict, db: Session = Depends(get_db)):
    svc = get_workspace_service()
    return svc.create_workspace(
        db, payload["name"],
        workspace_id=payload.get("workspace_id"),
        description=payload.get("description"),
    )


@router.get("/workspaces/{workspace_id}")
def get_workspace(workspace_id: str, db: Session = Depends(get_db)):
    svc = get_workspace_service()
    ws = svc.get_workspace(db, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws


@router.put("/workspaces/{workspace_id}")
def update_workspace(workspace_id: str, payload: dict, db: Session = Depends(get_db)):
    svc = get_workspace_service()
    ws = svc.update_workspace(
        db, workspace_id,
        name=payload.get("name"),
        description=payload.get("description"),
    )
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws


@router.delete("/workspaces/{workspace_id}")
def delete_workspace(workspace_id: str, db: Session = Depends(get_db)):
    svc = get_workspace_service()
    if not svc.delete_workspace(db, workspace_id):
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"status": "deleted"}
