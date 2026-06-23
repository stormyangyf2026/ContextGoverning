"""External API — Search endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.search_service import get_search_service

router = APIRouter(tags=["external-search"])


@router.post("/search")
def external_search(payload: dict, db: Session = Depends(get_db)):
    svc = get_search_service()
    return svc.search(
        db=db, query=payload.get("query", ""),
        mode=payload.get("mode", "hybrid"),
        filters=payload.get("filters"),
        page=payload.get("page", 1),
        page_size=payload.get("page_size", 20),
    )


@router.get("/search/suggestions")
def search_suggestions(q: str = "", db: Session = Depends(get_db)):
    return {"query": q, "suggestions": []}
