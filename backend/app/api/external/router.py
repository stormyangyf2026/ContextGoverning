"""External API router aggregation."""
from fastapi import APIRouter

external_router = APIRouter(prefix="/api/v1/external")

from app.api.external import auth, contexts, search, entities, workspaces, health

external_router.include_router(health.router)
external_router.include_router(auth.router)
external_router.include_router(contexts.router)
external_router.include_router(search.router)
external_router.include_router(entities.router)
external_router.include_router(workspaces.router)
