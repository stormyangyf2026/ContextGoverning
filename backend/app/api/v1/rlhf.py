"""Internal API v1 — RLHF Pipeline control endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import get_db
from app.services.feedback_service import build_training_dataset
from app.services.classification_learning_service import (
    learn_from_feedback, get_rules as get_classification_rules,
    evaluate_rules, rollback_rules,
)
from app.services.confidence_calibration_service import (
    calibrate_initial_confidence, calibrate_review_upgrade,
    detect_confidence_drift, calculate_weighted_confidence,
)
from app.models.review_feedback import FeedbackDataset, RuleLearningLog

router = APIRouter(prefix="/rlhf", tags=["rlhf"])


# ── Schemas ────────────────────────────────────────────────────

class BuildDatasetRequest(BaseModel):
    name: Optional[str] = None
    min_samples: int = Field(100, ge=50, le=5000)
    min_label_confidence: float = Field(0.7, ge=0.5, le=1.0)
    train_test_split: float = Field(0.8, ge=0.6, le=0.9)


class LearnRequest(BaseModel):
    dataset_id: Optional[str] = None
    auto_apply: bool = False
    min_accuracy_improvement: float = Field(0.02, ge=0.01, le=0.10)


class CalibrateRequest(BaseModel):
    learning_rate: float = Field(0.2, ge=0.05, le=0.5)


# ── Status ─────────────────────────────────────────────────────

@router.get("/status")
def get_rlhf_status(db: Session = Depends(get_db)):
    """Get RLHF pipeline status overview."""
    # Count feedback data
    from app.models.review_feedback import ReviewRecord, ClassificationLabel, ReviewerProfile
    total_reviews = db.query(ReviewRecord).count()
    total_labels = db.query(ClassificationLabel).count()
    active_reviewers = db.query(ReviewerProfile).filter(ReviewerProfile.is_active == True).count()

    # Count rules
    rules_count = len(get_classification_rules(db))

    # Latest learning
    latest_learning = db.query(RuleLearningLog).order_by(
        RuleLearningLog.created_at.desc()
    ).first()

    # Accuracy
    evaluation = evaluate_rules(db)

    return {
        "feedback_data": {
            "total_reviews": total_reviews,
            "total_labels": total_labels,
            "active_reviewers": active_reviewers,
            "ready_for_learning": total_labels >= 100,
        },
        "rules": {
            "total": rules_count,
            "active": evaluation["active_rules"],
            "deprecated": evaluation["deprecated_rules"],
            "overall_accuracy": evaluation["overall_accuracy"],
        },
        "latest_learning": {
            "id": str(latest_learning.id) if latest_learning else None,
            "trigger_source": latest_learning.trigger_source if latest_learning else None,
            "accuracy_improvement": latest_learning.accuracy_improvement if latest_learning else None,
            "status": latest_learning.status if latest_learning else None,
            "created_at": str(latest_learning.created_at) if latest_learning else None,
        } if latest_learning else None,
    }


# ── Datasets ───────────────────────────────────────────────────

@router.post("/datasets/build")
def build_dataset(
    payload: BuildDatasetRequest,
    db: Session = Depends(get_db),
):
    """Build a feedback dataset for training."""
    dataset = build_training_dataset(
        db,
        name=payload.name,
        min_samples=payload.min_samples,
        min_label_confidence=payload.min_label_confidence,
        train_test_split=payload.train_test_split,
    )
    if not dataset:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient feedback data. Need at least {payload.min_samples} validated labels.",
        )
    return {
        "id": str(dataset.id),
        "name": dataset.name,
        "version": dataset.version,
        "total_samples": dataset.total_samples,
        "accuracy_before": dataset.class_accuracy_before,
        "status": dataset.status,
    }


@router.get("/datasets")
def list_datasets(db: Session = Depends(get_db)):
    """List feedback datasets."""
    datasets = db.query(FeedbackDataset).order_by(
        FeedbackDataset.created_at.desc()
    ).limit(20).all()

    return [
        {
            "id": str(d.id),
            "name": d.name,
            "version": d.version,
            "dataset_type": d.dataset_type,
            "total_samples": d.total_samples,
            "class_accuracy_before": d.class_accuracy_before,
            "class_accuracy_after": d.class_accuracy_after,
            "status": d.status,
            "created_at": str(d.created_at),
        }
        for d in datasets
    ]


# ── Learning ───────────────────────────────────────────────────

@router.post("/learn")
def trigger_learning(
    payload: LearnRequest,
    db: Session = Depends(get_db),
):
    """Trigger a rule learning cycle."""
    log = learn_from_feedback(
        db,
        dataset_id=payload.dataset_id,
        auto_apply=payload.auto_apply,
        min_accuracy_improvement=payload.min_accuracy_improvement,
    )

    return {
        "id": str(log.id),
        "status": log.status,
        "rules_added": log.rules_added,
        "rules_updated": log.rules_updated,
        "rules_deprecated": log.rules_deprecated,
        "accuracy_before": log.accuracy_before,
        "accuracy_after": log.accuracy_after,
        "accuracy_improvement": log.accuracy_improvement,
        "duration_seconds": log.duration_seconds,
        "error_message": log.error_message,
    }


@router.get("/learn/logs")
def get_learning_logs(db: Session = Depends(get_db)):
    """Get rule learning execution logs."""
    logs = db.query(RuleLearningLog).order_by(
        RuleLearningLog.created_at.desc()
    ).limit(20).all()

    return [
        {
            "id": str(l.id),
            "trigger_source": l.trigger_source,
            "total_rules_before": l.total_rules_before,
            "accuracy_before": l.accuracy_before,
            "rules_added": l.rules_added,
            "rules_updated": l.rules_updated,
            "rules_deprecated": l.rules_deprecated,
            "accuracy_after": l.accuracy_after,
            "accuracy_improvement": l.accuracy_improvement,
            "status": l.status,
            "duration_seconds": l.duration_seconds,
            "top_new_keywords": l.top_new_keywords,
            "created_at": str(l.created_at),
        }
        for l in logs
    ]


@router.post("/learn/rollback/{log_id}")
def rollback_learning_result(log_id: str, db: Session = Depends(get_db)):
    """Roll back a learning result."""
    log = rollback_rules(db, None, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Learning log not found")
    return {"id": str(log.id), "status": log.status}


@router.post("/learn/preview")
def preview_learning(payload: LearnRequest, db: Session = Depends(get_db)):
    """Preview learning results without applying (dry run)."""
    # For preview, we run learn but don't auto-apply
    log = learn_from_feedback(
        db,
        dataset_id=payload.dataset_id,
        auto_apply=False,
        min_accuracy_improvement=0.0,  # always show results
    )
    return {
        "preview": True,
        "accuracy_before": log.accuracy_before,
        "accuracy_after": log.accuracy_after,
        "accuracy_improvement": log.accuracy_improvement,
        "rules_added": log.rules_added,
        "rules_updated": log.rules_updated,
        "rules_deprecated": log.rules_deprecated,
        "would_auto_apply": (log.accuracy_improvement or 0) >= payload.min_accuracy_improvement,
        "top_new_keywords": log.top_new_keywords,
    }


# ── Calibration ────────────────────────────────────────────────

@router.post("/calibrate")
def trigger_calibration(
    payload: CalibrateRequest,
    db: Session = Depends(get_db),
):
    """Trigger confidence calibration."""
    init_calib = calibrate_initial_confidence(db, learning_rate=payload.learning_rate)
    review_calib = calibrate_review_upgrade(db)

    significant_init = {k: v for k, v in init_calib.items() if v["significant"]}

    return {
        "initial_confidence_calibration": {
            "total_source_types": len(init_calib),
            "significant_changes": len(significant_init),
            "details": init_calib,
        },
        "review_upgrade_calibration": review_calib,
    }


@router.get("/calibrate/drift")
def check_confidence_drift(
    db: Session = Depends(get_db),
    period_days: int = 30,
):
    """Check for confidence score drift."""
    drifts = detect_confidence_drift(db, period_days=period_days)
    return {
        "drifts_detected": len(drifts),
        "alerts": drifts,
    }


# ── Metrics ────────────────────────────────────────────────────

@router.get("/metrics")
def get_rlhf_metrics(db: Session = Depends(get_db)):
    """Get RLHF effectiveness metrics."""
    evaluation = evaluate_rules(db)
    status = get_rlhf_status(db)

    return {
        "classification_accuracy": evaluation["overall_accuracy"],
        "active_rules": evaluation["active_rules"],
        "learned_rules": sum(
            1 for r in get_classification_rules(db) if r.source == "learned"
        ),
        "domain_stats": evaluation["domain_stats"],
        "feedback_data": status["feedback_data"],
        "latest_learning": status["latest_learning"],
    }


# ── Weighted Confidence (per-context) ──────────────────────────

@router.get("/weighted-confidence/{context_id}")
def get_weighted_confidence_endpoint(
    context_id: str,
    db: Session = Depends(get_db),
):
    """Get weighted confidence for a specific context."""
    result = calculate_weighted_confidence(db, context_id)
    if not result:
        raise HTTPException(status_code=404, detail="No reviews with confidence ratings found")
    return result
