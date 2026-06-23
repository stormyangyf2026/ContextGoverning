"""External API — Context endpoints (workspace-isolated)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.context_service import get_context, list_contexts, create_context

router = APIRouter(tags=["external-contexts"])


@router.get("/contexts")
def list_contexts_api(
    workspace_id: str = None,
    domain: str = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    return list_contexts(db, domain=domain, skip=skip, limit=limit)


@router.post("/contexts")
def create_context_api(payload: dict, db: Session = Depends(get_db)):
    try:
        return create_context(db, **payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/contexts/{context_id}")
def get_context_api(context_id: str, db: Session = Depends(get_db)):
    ctx = get_context(db, context_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="Context not found")
    return ctx


@router.put("/contexts/{context_id}")
def update_context_api(context_id: str, payload: dict, db: Session = Depends(get_db)):
    from app.services.context_service import update_context
    try:
        return update_context(db, context_id, **payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/contexts/{context_id}")
def delete_context_api(context_id: str, db: Session = Depends(get_db)):
    ctx = get_context(db, context_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="Context not found")
    ctx.is_deleted = True
    db.commit()
    return {"status": "deleted"}


@router.post("/contexts/batch")
def batch_import_contexts(payload: dict, db: Session = Depends(get_db)):
    items = payload.get("items", [])
    results = []
    for item in items:
        try:
            ctx = create_context(db, **item)
            results.append({"id": ctx.context_id, "status": "success"})
        except Exception as e:
            results.append({"status": "failed", "error": str(e)})
    return {"results": results, "total": len(items), "succeeded": len([r for r in results if r["status"] == "success"])}
