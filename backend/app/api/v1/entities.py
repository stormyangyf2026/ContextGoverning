"""Internal API v1 — Entity & Relation endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.entity_service import create_entity, get_entity, list_entities, update_entity
from app.services.relation_service import create_relation, get_relation, list_relations, delete_relation
from app.services.graph_service import get_graph_service

router = APIRouter()


# ── Entities ────────────────────────────────────────────────────

@router.get("/entities")
def list_entities_api(
    entity_type: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return list_entities(db, entity_type=entity_type, domain=domain, search=search, skip=skip, limit=limit)


@router.post("/entities")
def create_entity_api(
    payload: dict,
    db: Session = Depends(get_db),
):
    try:
        return create_entity(
            db, payload["name"], payload.get("type", "other"),
            domain=payload.get("domain"),
            aliases=payload.get("aliases"),
            metadata=payload.get("metadata"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/entities/graph")
def get_entity_graph_by_name_api(
    entity_name: str = Query(...),
    depth: int = Query(2, ge=1, le=3),
    db: Session = Depends(get_db),
):
    """Get entity graph by entity name (query param)."""
    svc = get_graph_service()
    result = svc.get_subgraph(db, entity_name=entity_name, depth=depth)
    if not result["center_entity"]:
        raise HTTPException(status_code=404, detail="Entity not found")
    return result


@router.get("/entities/{entity_id}")
def get_entity_api(
    entity_id: str,
    db: Session = Depends(get_db),
):
    entity = get_entity(db, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


@router.get("/entities/{entity_id}/graph")
def get_entity_graph_api(
    entity_id: str,
    depth: int = Query(2, ge=1, le=3),
    db: Session = Depends(get_db),
):
    svc = get_graph_service()
    result = svc.get_subgraph(db, entity_id=entity_id, depth=depth)
    if not result["center_entity"]:
        raise HTTPException(status_code=404, detail="Entity not found")
    return result


# ── Relations ───────────────────────────────────────────────────

@router.get("/relations")
def list_relations_api(
    context_id: Optional[str] = Query(None),
    relation_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return list_relations(db, context_id=context_id, relation_type=relation_type, skip=skip, limit=limit)


@router.post("/relations")
def create_relation_api(
    payload: dict,
    db: Session = Depends(get_db),
):
    try:
        return create_relation(
            db, payload["source_id"], payload["target_id"],
            payload.get("relation_type", "depends_on"),
            payload.get("created_by", "api"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/relations/{relation_id}")
def delete_relation_api(
    relation_id: str,
    db: Session = Depends(get_db),
):
    try:
        delete_relation(db, relation_id)
        return {"status": "deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
