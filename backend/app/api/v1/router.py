"""API v1 router aggregation."""
from fastapi import APIRouter

v1_router = APIRouter(prefix="/api/v1")

from app.api.v1 import context, search, entities, users, permissions, review, metrics, config
from app.api.v1 import feedback, classification_rules, rlhf  # RLHF new routes

v1_router.include_router(context.router)
v1_router.include_router(search.router)
v1_router.include_router(entities.router)
v1_router.include_router(users.router)
v1_router.include_router(permissions.router)
v1_router.include_router(review.router)
v1_router.include_router(metrics.router)
v1_router.include_router(config.router)
v1_router.include_router(feedback.router)
v1_router.include_router(classification_rules.router)
v1_router.include_router(rlhf.router)
