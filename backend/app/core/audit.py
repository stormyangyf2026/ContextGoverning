"""Audit logging interceptor — writes audit_logs entries for all data mutations.

Can be used as a FastAPI middleware or called directly from service layer.
"""
import json
from typing import Any, Optional
from sqlalchemy.orm import Session
from app.models.audit import AuditLog


def log_audit(
    db: Session,
    action: str,
    actor: str,
    context_id: Optional[str] = None,
    changes: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AuditLog:
    """Write an audit log entry to the database."""
    audit = AuditLog(
        action=action,
        actor=actor,
        context_id=context_id,
        changes=changes or {},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(audit)
    db.commit()
    return audit


def log_confidence_change(
    db: Session,
    actor: str,
    context_id: str,
    old_level: str,
    new_level: str,
    old_score: float,
    new_score: float,
    reason: str = "",
) -> AuditLog:
    """Specialized audit log for confidence level changes."""
    return log_audit(
        db=db,
        action="adjust_confidence",
        actor=actor,
        context_id=context_id,
        changes={
            "old_level": old_level,
            "new_level": new_level,
            "old_score": old_score,
            "new_score": new_score,
            "reason": reason,
        },
    )


def log_lifecycle_change(
    db: Session,
    actor: str,
    context_id: str,
    old_status: str,
    new_status: str,
    trigger: str = "",
) -> AuditLog:
    """Specialized audit log for lifecycle status changes."""
    return log_audit(
        db=db,
        action="update",
        actor=actor,
        context_id=context_id,
        changes={
            "field": "lifecycle_status",
            "old_status": old_status,
            "new_status": new_status,
            "trigger": trigger,
        },
    )


def log_config_change(
    db: Session,
    actor: str,
    section: str,
    config_key: str,
    old_value: Any,
    new_value: Any,
    reason: str = "",
) -> AuditLog:
    """Specialized audit log for configuration changes."""
    return log_audit(
        db=db,
        action="manage_config",
        actor=actor,
        changes={
            "section": section,
            "config_key": config_key,
            "old_value": json.dumps(old_value, default=str),
            "new_value": json.dumps(new_value, default=str),
            "reason": reason,
        },
    )
