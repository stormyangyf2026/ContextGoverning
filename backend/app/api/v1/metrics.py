"""Internal API v1 — Metrics endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.metrics_service import get_metrics_service

router = APIRouter(tags=["metrics"])


@router.get("/metrics/overview")
def get_overview(db: Session = Depends(get_db)):
    """Get platform overview metrics."""
    svc = get_metrics_service()
    return svc.get_overview(db)


@router.get("/metrics/coverage")
def get_coverage(db: Session = Depends(get_db)):
    """Get domain coverage metrics."""
    svc = get_metrics_service()
    return svc.get_coverage(db)


@router.get("/metrics/freshness")
def get_freshness(
    days: int = 30,
    db: Session = Depends(get_db),
):
    """Get data freshness metrics."""
    svc = get_metrics_service()
    return svc.get_freshness(db, days=days)


@router.get("/metrics/confidence-trends")
def get_confidence_trends(
    domain: str = None,
    days: int = 90,
    db: Session = Depends(get_db),
):
    """Get confidence score trends."""
    svc = get_metrics_service()
    return svc.get_confidence_trends(db, domain=domain, days=days)
