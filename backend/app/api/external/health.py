"""External API — Health check endpoints."""
from fastapi import APIRouter

router = APIRouter(tags=["external-health"])


@router.get("/health")
def health_check():
    """External health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


@router.get("/health/metrics")
def health_metrics():
    """External health metrics endpoint."""
    return {
        "status": "healthy",
        "uptime_seconds": 0,
        "memory_mb": 0,
        "connections": 0,
    }
