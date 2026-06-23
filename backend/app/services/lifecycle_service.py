"""Lifecycle state machine — manages the 8-state lifecycle of context items.

States: created → pending_review → active → decaying/needs_update/superseded/contradicted → archived

Auto-trigger rules (Design Doc §3.5):
    - N months no update → decaying (configurable via LIFECYCLE_AUTO_DECAY_MONTHS)
    - New version created → old marked superseded
    - Two active contexts contradict → both marked contradicted
    - Project ends + 2 years → archived

All timing thresholds read from Settings (env vars / .env file).
"""
from datetime import datetime, date, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.context import ContextItem
from app.core.audit import log_lifecycle_change
from app.config import get_settings

_settings = get_settings()


STATE_TRANSITIONS = {
    "created": ["pending_review", "archived"],
    "pending_review": ["active", "archived"],
    "active": ["decaying", "needs_update", "superseded", "contradicted", "archived"],
    "decaying": ["needs_update", "active", "archived"],
    "needs_update": ["active", "archived", "superseded"],
    "superseded": ["archived"],
    "contradicted": ["active", "archived"],
    "archived": ["active"],  # restore
}


def is_valid_transition(current: str, target: str) -> bool:
    """Check if a lifecycle transition is allowed."""
    return target in STATE_TRANSITIONS.get(current, [])


def transition(
    db: Session,
    actor: str,
    context: ContextItem,
    new_status: str,
) -> ContextItem:
    """Perform a lifecycle state transition with audit logging."""
    if not is_valid_transition(context.lifecycle_status, new_status):
        raise ValueError(
            f"Invalid transition: {context.lifecycle_status} → {new_status}"
        )

    old_status = context.lifecycle_status
    context.lifecycle_status = new_status

    if new_status == "active":
        context.lifecycle_valid_from = date.today()
        # Immutability for L3+ active contexts
        if context.confidence_level in ("L3", "L4", "L5"):
            context.is_immutable = True
    elif new_status == "archived":
        context.archived_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(context)
    log_lifecycle_change(db, actor, context.id, old_status, new_status)
    return context


def auto_trigger_decay(db: Session) -> List[ContextItem]:
    """Daily check: decay contexts not updated in > N months (called by scheduler).
    
    The threshold N is read from Settings (LIFECYCLE_AUTO_DECAY_MONTHS, default 6).
    """
    decay_months = _settings.lifecycle_auto_decay_months
    today = date.today()
    # Calculate threshold date by subtracting decay_months
    month = today.month - decay_months
    year = today.year
    while month <= 0:
        month += 12
        year -= 1
    threshold_date = today.replace(year=year, month=month)

    stale = (
        db.query(ContextItem)
        .filter(
            ContextItem.lifecycle_status == "active",
            ContextItem.updated_at < threshold_date,
        )
        .all()
    )

    decayed = []
    for ctx in stale:
        ctx.lifecycle_status = "decaying"
        decayed.append(ctx)
        log_lifecycle_change(
            db, "system:scheduler", ctx.id,
            old_status="active", new_status="decaying",
            trigger=f"auto_decay_{_settings.lifecycle_auto_decay_months}months",
        )

    if decayed:
        db.commit()
    return decayed


def auto_trigger_supersede(
    db: Session, old_context: ContextItem, new_context_id: str
) -> None:
    """Mark old context as superseded when a new version is created."""
    old_context.lifecycle_status = "superseded"
    old_context.superseded_by = new_context_id
    db.commit()
    log_lifecycle_change(
        db, "system", old_context.id,
        old_status="active", new_status="superseded",
        trigger=f"new_version:{new_context_id}",
    )
