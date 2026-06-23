"""Metrics service — KPI collection and analysis for the Context Platform.

Provides coverage, freshness, confidence distribution, and other KPIs.
All configuration via Settings/env (no hardcoded values).
"""
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone, timedelta
from app.models.context import ContextItem
from app.models.entity import Entity
from app.models.relation import Relation
from app.config import get_settings


class MetricsService:
    """KPI collection and analysis service."""

    def get_overview(self, db: Session) -> Dict[str, Any]:
        """Get platform overview metrics."""
        total_contexts = db.query(func.count(ContextItem.id)).filter(
            ContextItem.is_deleted == False
        ).scalar() or 0

        total_entities = db.query(func.count(Entity.id)).scalar() or 0
        total_relations = db.query(func.count(Relation.id)).scalar() or 0

        # Confidence distribution
        conf_dist = (
            db.query(
                ContextItem.confidence_level,
                func.count(ContextItem.id),
            )
            .filter(ContextItem.is_deleted == False)
            .group_by(ContextItem.confidence_level)
            .all()
        )
        confidence_distribution = {level or "unknown": count for level, count in conf_dist}

        return {
            "total_contexts": total_contexts,
            "total_entities": total_entities,
            "total_relations": total_relations,
            "confidence_distribution": confidence_distribution,
            "collected_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_coverage(self, db: Session) -> Dict[str, Any]:
        """Get domain coverage metrics."""
        domain_dist = (
            db.query(
                ContextItem.domain,
                func.count(ContextItem.id),
            )
            .filter(ContextItem.is_deleted == False)
            .group_by(ContextItem.domain)
            .all()
        )
        coverage = {domain or "unknown": count for domain, count in domain_dist}
        return {"domain_coverage": coverage}

    def get_freshness(
        self,
        db: Session,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get data freshness metrics."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=days)

        recent_count = db.query(func.count(ContextItem.id)).filter(
            ContextItem.is_deleted == False,
            ContextItem.created_at >= cutoff,
        ).scalar() or 0

        count_result = db.query(func.count(ContextItem.id)).filter(
            ContextItem.is_deleted == False
        ).scalar()
        total_count = count_result or 0

        # Lifecycle status distribution
        lifecycle_dist = (
            db.query(
                ContextItem.lifecycle_status,
                func.count(ContextItem.id),
            )
            .filter(ContextItem.is_deleted == False)
            .group_by(ContextItem.lifecycle_status)
            .all()
        )
        lifecycle = {status or "unknown": count for status, count in lifecycle_dist}

        return {
            "recent_contexts": recent_count,
            "total_contexts": total_count,
            "freshness_ratio": round(recent_count / total_count, 3) if total_count > 0 else 0.0,
            "evaluation_period_days": days,
            "lifecycle_status": lifecycle,
        }

    def get_confidence_trends(
        self,
        db: Session,
        domain: Optional[str] = None,
        days: int = 90,
    ) -> List[Dict[str, Any]]:
        """Get confidence score trends over time."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=days)

        conditions = [
            ContextItem.is_deleted == False,
            ContextItem.created_at >= cutoff,
        ]
        if domain:
            conditions.append(ContextItem.domain == domain)

        contexts = (
            db.query(ContextItem)
            .filter(*conditions)
            .order_by(ContextItem.created_at.asc())
            .all()
        )

        trends = []
        for ctx in contexts:
            trends.append({
                "date": ctx.created_at.strftime("%Y-%m-%d") if ctx.created_at else None,
                "confidence_score": ctx.confidence_score or 0,
                "confidence_level": ctx.confidence_level,
            })
        return trends


# Singleton
_metrics_service: Optional[MetricsService] = None


def get_metrics_service() -> MetricsService:
    global _metrics_service
    if _metrics_service is None:
        _metrics_service = MetricsService()
    return _metrics_service
