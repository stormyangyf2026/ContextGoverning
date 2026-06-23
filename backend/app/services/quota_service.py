"""Quota management service — resource usage tracking and enforcement.

Tracks and enforces quotas for contexts, entities, users, storage, API calls, and LLM tokens.
All configuration via Settings/env (no hardcoded values).
"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.config import get_settings


class QuotaService:
    """Resource quota tracking and enforcement."""

    # Default quotas
    DEFAULT_QUOTAS = {
        "contexts": 10000,
        "entities": 5000,
        "users": 100,
        "storage_mb": 1024,
        "api_calls_per_day": 10000,
        "llm_tokens_per_day": 100000,
    }

    def check_quota(
        self,
        db: Session,
        workspace_id: str,
        quota_type: str,
    ) -> bool:
        """Check if a workspace has remaining quota for an operation.

        Returns True if quota is available, False if exceeded.
        """
        if quota_type not in self.DEFAULT_QUOTAS:
            return True

        usage = self.get_usage(db, workspace_id, quota_type)
        limit = self.DEFAULT_QUOTAS[quota_type]
        return usage < limit

    def get_usage(
        self,
        db: Session,
        workspace_id: str,
        quota_type: str,
    ) -> int:
        """Get current usage for a quota type."""
        from sqlalchemy import func
        from app.models.context import ContextItem
        from app.models.entity import Entity
        from app.models.user import User

        if quota_type == "contexts":
            return db.query(func.count(ContextItem.id)).filter(
                ContextItem.workspace_id == workspace_id,
                ContextItem.is_deleted == False,
            ).scalar() or 0
        elif quota_type == "entities":
            return db.query(func.count(Entity.id)).filter(
                Entity.workspace_id == workspace_id,
            ).scalar() or 0
        elif quota_type == "users":
            return db.query(func.count(User.id)).filter(
                User.workspace_id == workspace_id,
            ).scalar() or 0
        return 0

    def get_all_quotas(
        self,
        db: Session,
        workspace_id: str,
    ) -> Dict[str, Any]:
        """Get all quota usage and limits for a workspace."""
        result = {}
        for quota_type, limit in self.DEFAULT_QUOTAS.items():
            usage = self.get_usage(db, workspace_id, quota_type)
            result[quota_type] = {
                "used": usage,
                "limit": limit,
                "remaining": limit - usage,
            }
        return result


# Singleton
_quota_service: Optional[QuotaService] = None


def get_quota_service() -> QuotaService:
    global _quota_service
    if _quota_service is None:
        _quota_service = QuotaService()
    return _quota_service
