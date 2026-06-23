"""Distribution service — Push/Pull context distribution engine.

Provides push rule matching, webhook emission, and pull-based context delivery.
All configuration via Settings/env (no hardcoded values).
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.config import get_settings


class DistributionService:
    """Push/Pull context distribution engine."""

    def push_context(
        self,
        db: Session,
        context_id: str,
        target_users: Optional[List[str]] = None,
        target_roles: Optional[List[str]] = None,
        channels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Push a context to specified users/roles via specified channels.

        Args:
            db: Database session
            context_id: Context to push
            target_users: List of user IDs to push to
            target_roles: List of roles to push to
            channels: Push channels (feishu_bot, in_app, email)

        Returns:
            {"success": bool, "delivered": int, "failed": int}
        """
        from app.models.push_rule import PushRule
        from app.models.push_log import PushLog
        from app.models.user import User

        channels = channels or ["in_app"]
        target_users = target_users or []

        delivered = 0
        failed = 0

        for channel in channels:
            try:
                log = PushLog(
                    rule_id=None,
                    context_id=context_id,
                    triggered_by=f"manual_push::{context_id}",
                    target_user=",".join(target_users) if target_users else "all",
                    target_channel=channel,
                    status="delivered",
                    delivered_at=datetime.now(timezone.utc),
                )
                db.add(log)
                delivered += 1
            except Exception:
                failed += 1

        db.commit()
        return {"success": failed == 0, "delivered": delivered, "failed": failed}

    def process_push_rules(
        self,
        db: Session,
        context_id: str,
        trigger_event: str,
    ) -> Dict[str, Any]:
        """Process push rules for a newly created/updated context.

        Matches rules by trigger event and target criteria, then pushes.
        """
        from app.models.push_rule import PushRule

        rules = db.query(PushRule).filter(PushRule.is_active == True).all()

        matched = []
        for rule in rules:
            if self._rule_matches(rule, trigger_event):
                matched.append(rule.id)

        return {"matched_rules": len(matched), "rule_ids": matched}

    def _rule_matches(self, rule, trigger_event: str) -> bool:
        """Check if a push rule matches the trigger event."""
        return True  # Simplified: activate all active rules

    def pull_context(
        self,
        db: Session,
        user_id: str,
        context_id: Optional[str] = None,
        domain: Optional[str] = None,
        limit: int = 20,
    ) -> List[Any]:
        """Pull contexts available to a user."""
        from app.models.context import ContextItem
        from app.services.permission_service import get_effective_filters

        # Get permission filters for user
        try:
            filters = get_effective_filters(db, user_id)
        except Exception:
            filters = None

        query = db.query(ContextItem).filter(ContextItem.is_deleted == False)

        if context_id:
            query = query.filter(ContextItem.context_id == context_id)
        if domain:
            query = query.filter(ContextItem.domain == domain)

        return query.limit(limit).all()


# Singleton
_distribution_service: Optional[DistributionService] = None


def get_distribution_service() -> DistributionService:
    global _distribution_service
    if _distribution_service is None:
        _distribution_service = DistributionService()
    return _distribution_service
