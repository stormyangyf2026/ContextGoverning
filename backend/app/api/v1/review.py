"""Internal API v1 — Enhanced review queue endpoints with structured RLHF feedback."""
from typing import Optional, List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.context import ContextItem
from app.models.review_feedback import ReviewRecord
from app.services.feedback_service import (
    submit_review_feedback,
    get_feedback_stats,
)


router = APIRouter(tags=["review"])


# ── Request / Response Schemas ─────────────────────────────────

class ReviewDecisionRequest(BaseModel):
    """Structured review decision with full feedback."""
    decision: str = Field(..., description="approved / rejected / needs_revision")
    reject_reason: Optional[str] = Field(None, description="incorrect_classification / outdated / low_quality / duplicate / irrelevant / other")
    corrected_domain: Optional[str] = None
    corrected_sub_category: Optional[str] = None
    original_domain: Optional[str] = None
    original_sub_category: Optional[str] = None
    confidence_rating: Optional[int] = Field(None, ge=1, le=5, description="1-5 star confidence rating")
    confidence_adjustment: Optional[str] = Field(None, description="upgrade / downgrade / confirm / none")
    adjusted_confidence_level: Optional[str] = None
    adjusted_confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    quality_score: Optional[int] = Field(None, ge=1, le=5)
    quality_dimensions: Optional[dict] = None
    review_comment: Optional[str] = None
    review_duration_seconds: Optional[int] = None
    priority: str = "normal"


class BatchReviewRequest(BaseModel):
    """Batch review request."""
    context_ids: List[str]
    decision: str = "approved"
    review_comment: Optional[str] = None


class ReviewStatsResponse(BaseModel):
    total_reviews: int
    approved: int
    rejected: int
    needs_revision: int
    classification_accuracy: float
    avg_confidence_rating: float
    avg_quality_score: float


# ── Review Queue ───────────────────────────────────────────────

@router.get("/review/queue")
def get_review_queue(
    db: Session = Depends(get_db),
    domain: Optional[str] = None,
    status: Optional[str] = Query(None, alias="lifecycle_status"),
    sort_by: str = "created",
    skip: int = 0,
    limit: int = 20,
):
    """Get pending review items with optional filters."""
    query = db.query(ContextItem).filter(
        ContextItem.lifecycle_status == "pending_review",
        ContextItem.is_deleted == False,
    )
    if domain:
        query = query.filter(ContextItem.domain == domain)

    if sort_by == "priority":
        query = query.order_by(ContextItem.confidence_level.asc(), ContextItem.created_at.desc())
    elif sort_by == "confidence":
        query = query.order_by(ContextItem.confidence_level.asc())
    else:
        query = query.order_by(ContextItem.created_at.desc())

    items = query.offset(skip).limit(limit).all()

    # Enrich with review stats
    result = []
    for item in items:
        review_count = db.query(ReviewRecord).filter(
            ReviewRecord.context_id == item.id
        ).count()
        item_dict = {
            "id": str(item.id),
            "context_id": item.context_id,
            "title": item.title,
            "domain": item.domain,
            "sub_category": item.sub_category,
            "confidence_level": item.confidence_level,
            "confidence_score": item.confidence_score,
            "lifecycle_status": item.lifecycle_status,
            "source_system": item.source_system,
            "created_at": str(item.created_at),
            "review_count": review_count,
        }
        result.append(item_dict)

    return result


@router.get("/review/queue/smart")
def get_smart_review_queue(
    db: Session = Depends(get_db),
    reviewer_id: Optional[str] = None,
    limit: int = 20,
):
    """Smart-sorted review queue: prioritize high-impact items, reviewer domain expertise."""
    query = db.query(ContextItem).filter(
        ContextItem.lifecycle_status == "pending_review",
        ContextItem.is_deleted == False,
    )

    # Prioritize: lower confidence first, then newer items
    items = query.order_by(
        ContextItem.confidence_level.asc(),
        ContextItem.created_at.desc(),
    ).limit(limit * 2).all()

    result = []
    for item in items:
        # Check if already reviewed
        existing = db.query(ReviewRecord).filter(
            ReviewRecord.context_id == item.id,
        ).first()
        result.append({
            "id": str(item.id),
            "context_id": item.context_id,
            "title": item.title,
            "domain": item.domain,
            "confidence_level": item.confidence_level,
            "lifecycle_status": item.lifecycle_status,
            "source_system": item.source_system,
            "created_at": str(item.created_at),
            "already_reviewed": existing is not None,
            "priority": "high" if item.confidence_level in ("L0", "L1", "L2") else "normal",
        })

    return result[:limit]


# ── Structured Review Decision ─────────────────────────────────

@router.post("/review/{context_id}/decide")
def review_decide(
    context_id: str,
    decision_payload: ReviewDecisionRequest,
    db: Session = Depends(get_db),
):
    """Submit a structured review decision with full RLHF feedback."""
    from app.services.context_service import get_context
    from app.services.lifecycle_service import transition

    ctx = get_context(db, context_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="Context not found")

    # Perform lifecycle transition
    if decision_payload.decision == "approved":
        new_status = "active"
    elif decision_payload.decision == "rejected":
        new_status = "created"
    else:
        # needs_revision: keep pending_review
        new_status = "pending_review"

    try:
        if new_status != ctx.lifecycle_status:
            transition(db, "system:reviewer", ctx, new_status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Submit structured feedback
    record = submit_review_feedback(
        db=db,
        reviewer_id="system:reviewer",  # TODO: get from auth context
        context_id=str(ctx.id),
        decision=decision_payload.decision,
        reject_reason=decision_payload.reject_reason,
        corrected_domain=decision_payload.corrected_domain,
        corrected_sub_category=decision_payload.corrected_sub_category,
        original_domain=decision_payload.original_domain,
        original_sub_category=decision_payload.original_sub_category,
        confidence_rating=decision_payload.confidence_rating,
        confidence_adjustment=decision_payload.confidence_adjustment,
        adjusted_confidence_level=decision_payload.adjusted_confidence_level,
        adjusted_confidence_score=decision_payload.adjusted_confidence_score,
        quality_score=decision_payload.quality_score,
        quality_dimensions=decision_payload.quality_dimensions,
        review_comment=decision_payload.review_comment,
        review_duration_seconds=decision_payload.review_duration_seconds,
        priority=decision_payload.priority,
    )

    # Update context classification tracking
    if decision_payload.corrected_domain:
        ctx.classification_source = "manual"
        ctx.auto_classification_correct = False
    elif decision_payload.decision == "approved":
        ctx.auto_classification_correct = True
    db.commit()

    return {
        "status": "success",
        "decision": decision_payload.decision,
        "new_lifecycle_status": ctx.lifecycle_status,
        "review_id": str(record.id),
    }


# ── Legacy approve/reject (backward compat) ────────────────────

@router.post("/review/{context_id}/approve")
def approve_context(
    context_id: str,
    db: Session = Depends(get_db),
):
    """[Legacy] Approve a context to active."""
    from app.services.context_service import get_context
    ctx = get_context(db, context_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="Context not found")
    ctx.lifecycle_status = "active"
    ctx.auto_classification_correct = True
    ctx.verified_by = "system:reviewer"
    ctx.verified_at = datetime.now(timezone.utc)
    db.commit()

    # Also create a review record
    submit_review_feedback(
        db=db, reviewer_id="system:reviewer",
        context_id=str(ctx.id), decision="approved",
    )
    return {"status": "approved"}


@router.post("/review/{context_id}/reject")
def reject_context(
    context_id: str,
    db: Session = Depends(get_db),
):
    """[Legacy] Reject a context."""
    from app.services.context_service import get_context
    ctx = get_context(db, context_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="Context not found")
    ctx.lifecycle_status = "created"
    db.commit()

    submit_review_feedback(
        db=db, reviewer_id="system:reviewer",
        context_id=str(ctx.id), decision="rejected",
    )
    return {"status": "rejected"}


# ── Review Statistics ──────────────────────────────────────────

@router.get("/review/stats")
def get_review_stats(
    db: Session = Depends(get_db),
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
):
    """Get review statistics for the admin dashboard."""
    start_dt = None
    end_dt = None
    if period_start:
        start_dt = datetime.fromisoformat(period_start)
    if period_end:
        end_dt = datetime.fromisoformat(period_end)

    stats = get_feedback_stats(db, period_start=start_dt, period_end=end_dt)

    # Add queue stats
    pending_count = db.query(ContextItem).filter(
        ContextItem.lifecycle_status == "pending_review",
        ContextItem.is_deleted == False,
    ).count()

    stats["pending_queue_size"] = pending_count
    return stats


@router.get("/review/history")
def get_review_history(
    db: Session = Depends(get_db),
    context_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
):
    """Get review history for a context or all recent reviews."""
    query = db.query(ReviewRecord)
    if context_id:
        query = query.filter(ReviewRecord.context_id == context_id)
    reviews = query.order_by(ReviewRecord.created_at.desc()).offset(skip).limit(limit).all()

    return [
        {
            "id": str(r.id),
            "context_id": str(r.context_id),
            "reviewer_id": str(r.reviewer_id),
            "decision": r.decision,
            "classification_correct": r.classification_correct,
            "confidence_rating": r.confidence_rating,
            "quality_score": r.quality_score,
            "review_comment": r.review_comment,
            "is_golden_sample": r.is_golden_sample,
            "created_at": str(r.created_at),
        }
        for r in reviews
    ]


@router.post("/review/batch")
def batch_review(
    payload: BatchReviewRequest,
    db: Session = Depends(get_db),
):
    """Batch approve or reject multiple contexts."""
    from app.services.context_service import get_context
    results = []
    for ctx_id in payload.context_ids:
        ctx = get_context(db, ctx_id)
        if not ctx:
            results.append({"context_id": ctx_id, "status": "not_found"})
            continue

        old_status = ctx.lifecycle_status
        if payload.decision == "approved":
            ctx.lifecycle_status = "active"
        else:
            ctx.lifecycle_status = "created"

        submit_review_feedback(
            db=db, reviewer_id="system:reviewer",
            context_id=str(ctx.id), decision=payload.decision,
            review_comment=payload.review_comment,
        )
        results.append({
            "context_id": ctx_id,
            "status": "success",
            "old_status": old_status,
            "new_status": ctx.lifecycle_status,
        })

    db.commit()
    return {"results": results, "total": len(results)}
