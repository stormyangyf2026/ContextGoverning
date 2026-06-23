"""Internal API v1 — RLHF Feedback management endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import get_db
from app.services.feedback_service import (
    submit_classification_label,
    get_feedback_stats,
    get_reviewer_profile,
    calculate_reviewer_weight,
    update_all_reviewer_weights,
    detect_feedback_anomalies,
    mark_golden_sample,
    get_golden_samples,
)

router = APIRouter(prefix="/feedback", tags=["feedback"])


# ── Schemas ────────────────────────────────────────────────────

class SubmitLabelRequest(BaseModel):
    context_id: str
    label_type: str = Field(..., description="domain / sub_category / tag")
    predicted_value: Optional[str] = None
    corrected_value: str
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    label_source: str = "review"


class MarkGoldenSampleRequest(BaseModel):
    context_id: str


# ── Classification Labels ──────────────────────────────────────

@router.post("/labels")
def create_label(
    payload: SubmitLabelRequest,
    db: Session = Depends(get_db),
):
    """Submit a classification label/correction."""
    label = submit_classification_label(
        db=db,
        labeler_id="system:user",  # TODO: get from auth context
        context_id=payload.context_id,
        label_type=payload.label_type,
        predicted_value=payload.predicted_value,
        corrected_value=payload.corrected_value,
        confidence=payload.confidence,
        label_source=payload.label_source,
    )
    return {"id": str(label.id), "status": "created"}


@router.get("/labels")
def list_labels(
    db: Session = Depends(get_db),
    label_type: Optional[str] = None,
    min_confidence: float = 0.7,
    skip: int = 0,
    limit: int = 50,
):
    """List classification labels."""
    from app.models.review_feedback import ClassificationLabel
    query = db.query(ClassificationLabel)
    if label_type:
        query = query.filter(ClassificationLabel.label_type == label_type)
    query = query.filter(ClassificationLabel.confidence >= min_confidence)
    labels = query.order_by(ClassificationLabel.created_at.desc()).offset(skip).limit(limit).all()

    return [
        {
            "id": str(l.id),
            "context_id": str(l.context_id),
            "label_type": l.label_type,
            "predicted_value": l.predicted_value,
            "corrected_value": l.corrected_value,
            "confidence": l.confidence,
            "label_source": l.label_source,
            "is_validated": l.is_validated,
        }
        for l in labels
    ]


# ── Feedback Statistics ────────────────────────────────────────

@router.get("/stats")
def feedback_stats(
    db: Session = Depends(get_db),
):
    """Get comprehensive feedback statistics."""
    return get_feedback_stats(db)


# ── Reviewer Profile ───────────────────────────────────────────

@router.get("/reviewer/{user_id}")
def reviewer_profile(user_id: str, db: Session = Depends(get_db)):
    """Get a reviewer's performance profile."""
    profile = get_reviewer_profile(db, user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Reviewer profile not found")
    return profile


@router.post("/reviewer/{user_id}/recalculate-weight")
def recalculate_reviewer_weight(user_id: str, db: Session = Depends(get_db)):
    """Recalculate a reviewer's weight."""
    weight = calculate_reviewer_weight(db, user_id)
    return {"user_id": user_id, "reviewer_weight": weight}


@router.post("/reviewer/recalculate-all")
def recalculate_all_weights(db: Session = Depends(get_db)):
    """Recalculate weights for all active reviewers."""
    update_all_reviewer_weights(db)
    return {"status": "completed"}


# ── Anomaly Detection ──────────────────────────────────────────

@router.get("/anomalies")
def get_anomalies(db: Session = Depends(get_db)):
    """Detect anomalous feedback patterns."""
    return detect_feedback_anomalies(db)


# ── Golden Samples ─────────────────────────────────────────────

@router.get("/golden-samples")
def list_golden_samples(
    db: Session = Depends(get_db),
    limit: int = 50,
):
    """Get golden sample contexts."""
    samples = get_golden_samples(db, limit=limit)
    return [
        {
            "id": str(s.id),
            "context_id": str(s.context_id),
            "reviewer_id": str(s.reviewer_id),
            "decision": s.decision,
            "classification_correct": s.classification_correct,
            "created_at": str(s.created_at),
        }
        for s in samples
    ]


@router.post("/golden-samples/{context_id}")
def mark_as_golden(
    context_id: str,
    db: Session = Depends(get_db),
):
    """Mark a context's review as a golden sample."""
    record = mark_golden_sample(db, context_id, "system:admin")
    return {"id": str(record.id), "is_golden_sample": record.is_golden_sample}
