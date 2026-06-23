"""External API — Entity & Graph endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.entity_service import create_entity, get_entity, list_entities
from app.services.graph_service import get_graph_service

router = APIRouter(tags=["external-entities"])


@router.get("/entities")
def list_entities_api(
    entity_type: str = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    return list_entities(db, entity_type=entity_type, skip=skip, limit=limit)


@router.post("/entities")
def upsert_entity_api(payload: dict, db: Session = Depends(get_db)):
    """Create or update entity (upsert by name+type)."""
    try:
        return create_entity(
            db, payload["name"], payload.get("type", "other"),
            domain=payload.get("domain"),
            aliases=payload.get("aliases"),
            metadata=payload.get("metadata"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/entities/{entity_id}")
def get_entity_api(entity_id: str, db: Session = Depends(get_db)):
    entity = get_entity(db, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


@router.get("/entities/{entity_id}/graph")
def entity_graph_api(
    entity_id: str,
    depth: int = 2,
    db: Session = Depends(get_db),
):
    svc = get_graph_service()
    result = svc.get_subgraph(db, entity_id=entity_id, depth=depth)
    if not result["center_entity"]:
        raise HTTPException(status_code=404, detail="Entity not found")
    return result
