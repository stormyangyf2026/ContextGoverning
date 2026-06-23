"""Internal API v1 — Search endpoint."""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.search_service import get_search_service

router = APIRouter(tags=["search"])


@router.post("/search")
def search_api(
    payload: dict,
    db: Session = Depends(get_db),
):
    """Hybrid search with mode routing.

    Request body:
    {
        "query": "search text",
        "mode": "hybrid",
        "filters": {},
        "page": 1,
        "page_size": 20
    }
    """
    svc = get_search_service()
    return svc.search(
        db=db,
        query=payload.get("query", ""),
        mode=payload.get("mode", "hybrid"),
        filters=payload.get("filters"),
        page=payload.get("page", 1),
        page_size=payload.get("page_size", 20),
        include_relations=payload.get("include_relations", False),
        include_confidence_detail=payload.get("include_confidence_detail", False),
    )
