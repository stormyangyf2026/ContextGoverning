"""RLHF feedback service — collect, aggregate, and analyze human review feedback."""
import json
import statistics
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.review_feedback import (
    ReviewRecord, ClassificationLabel, ClassificationRuleWeight,
    FeedbackDataset, ReviewerProfile, RuleLearningLog,
)
from app.models.context import ContextItem
from app.core.audit import log_audit


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Review Feedback Submission ──────────────────────────────────

def submit_review_feedback(
    db: Session,
    reviewer_id: str,
    context_id: str,
    decision: str,
    reject_reason: Optional[str] = None,
    corrected_domain: Optional[str] = None,
    corrected_sub_category: Optional[str] = None,
    original_domain: Optional[str] = None,
    original_sub_category: Optional[str] = None,
    confidence_rating: Optional[int] = None,
    confidence_adjustment: Optional[str] = None,
    adjusted_confidence_level: Optional[str] = None,
    adjusted_confidence_score: Optional[float] = None,
    quality_score: Optional[int] = None,
    quality_dimensions: Optional[Dict] = None,
    review_comment: Optional[str] = None,
    review_duration_seconds: Optional[int] = None,
    priority: str = "normal",
) -> ReviewRecord:
    """Submit a structured review decision with full feedback."""
    # Determine if classification was correct
    classification_correct = None
    if corrected_domain is None and corrected_sub_category is None:
        classification_correct = True
    elif corrected_domain is not None or corrected_sub_category is not None:
        classification_correct = False

    record = ReviewRecord(
        context_id=context_id,
        reviewer_id=reviewer_id,
        decision=decision,
        reject_reason=reject_reason,
        corrected_domain=corrected_domain,
        corrected_sub_category=corrected_sub_category,
        original_domain=original_domain,
        original_sub_category=original_sub_category,
        classification_correct=classification_correct,
        confidence_rating=confidence_rating,
        confidence_adjustment=confidence_adjustment,
        adjusted_confidence_level=adjusted_confidence_level,
        adjusted_confidence_score=adjusted_confidence_score,
        quality_score=quality_score,
        quality_dimensions=json.dumps(quality_dimensions) if quality_dimensions else None,
        review_comment=review_comment,
        review_duration_seconds=review_duration_seconds,
        priority=priority,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # Update reviewer profile counters
    _update_reviewer_profile(db, reviewer_id, record)

    # If classification was corrected, create a classification label
    if not classification_correct and corrected_domain:
        submit_classification_label(
            db, reviewer_id, context_id, "domain",
            original_domain, corrected_domain,
            confidence=0.9 if decision == "approved" else 0.7,
        )

    # Log audit
    log_audit(db, "review_decide", str(reviewer_id), context_id,
              {"decision": decision, "confidence_rating": confidence_rating})

    return record


def _update_reviewer_profile(db: Session, reviewer_id: str, record: ReviewRecord):
    """Update reviewer profile counters after a review."""
    profile = db.query(ReviewerProfile).filter(
        ReviewerProfile.user_id == reviewer_id
    ).first()

    if not profile:
        profile = ReviewerProfile(
            user_id=reviewer_id,
            total_reviews=1,
        )
        db.add(profile)
    else:
        profile.total_reviews = (profile.total_reviews or 0) + 1

    if record.decision == "approved":
        profile.approved_count = (profile.approved_count or 0) + 1
    elif record.decision == "rejected":
        profile.rejected_count = (profile.rejected_count or 0) + 1
    elif record.decision == "needs_revision":
        profile.needs_revision_count = (profile.needs_revision_count or 0) + 1

    profile.last_review_at = utcnow()
    if record.review_duration_seconds:
        old_dur = profile.avg_review_duration or 0
        n = profile.total_reviews
        profile.avg_review_duration = (old_dur * (n - 1) + record.review_duration_seconds) / n

    db.commit()


# ── Classification Labels ──────────────────────────────────────

def submit_classification_label(
    db: Session,
    labeler_id: str,
    context_id: str,
    label_type: str,
    predicted_value: Optional[str],
    corrected_value: str,
    confidence: float = 1.0,
    label_source: str = "review",
) -> ClassificationLabel:
    """Submit a classification label (correction)."""
    label = ClassificationLabel(
        context_id=context_id,
        labeler_id=labeler_id,
        label_type=label_type,
        predicted_value=predicted_value,
        corrected_value=corrected_value,
        confidence=confidence,
        label_source=label_source,
    )
    db.add(label)
    db.commit()
    db.refresh(label)
    return label


def get_validated_labels(
    db: Session,
    workspace_id: Optional[str] = None,
    min_confidence: float = 0.7,
    label_type: Optional[str] = None,
    limit: int = 1000,
) -> List[ClassificationLabel]:
    """Get validated classification labels for training."""
    query = db.query(ClassificationLabel).filter(
        ClassificationLabel.confidence >= min_confidence,
    )
    if workspace_id:
        query = query.filter(ClassificationLabel.workspace_id == workspace_id)
    if label_type:
        query = query.filter(ClassificationLabel.label_type == label_type)
    return query.order_by(ClassificationLabel.created_at.desc()).limit(limit).all()


# ── Feedback Statistics ────────────────────────────────────────

def get_feedback_stats(
    db: Session,
    workspace_id: Optional[str] = None,
    period_start: Optional[datetime] = None,
    period_end: Optional[datetime] = None,
) -> Dict:
    """Get feedback statistics."""
    query = db.query(ReviewRecord)
    if workspace_id:
        query = query.filter(ReviewRecord.workspace_id == workspace_id)
    if period_start:
        query = query.filter(ReviewRecord.created_at >= period_start)
    if period_end:
        query = query.filter(ReviewRecord.created_at <= period_end)

    total = query.count()
    approved = query.filter(ReviewRecord.decision == "approved").count()
    rejected = query.filter(ReviewRecord.decision == "rejected").count()
    needs_revision = query.filter(ReviewRecord.decision == "needs_revision").count()
    class_correct = query.filter(ReviewRecord.classification_correct == True).count()
    class_correct_total = query.filter(ReviewRecord.classification_correct.isnot(None)).count()
    classification_accuracy = (class_correct / class_correct_total * 100) if class_correct_total > 0 else 0

    # Top error patterns
    error_patterns = (
        db.query(
            ReviewRecord.original_domain,
            ReviewRecord.corrected_domain,
            func.count(ReviewRecord.id).label("count"),
        )
        .filter(
            ReviewRecord.classification_correct == False,
            ReviewRecord.original_domain.isnot(None),
            ReviewRecord.corrected_domain.isnot(None),
        )
    )
    if workspace_id:
        error_patterns = error_patterns.filter(ReviewRecord.workspace_id == workspace_id)
    error_patterns = error_patterns.group_by(
        ReviewRecord.original_domain, ReviewRecord.corrected_domain
    ).order_by(func.count(ReviewRecord.id).desc()).limit(10).all()

    return {
        "total_reviews": total,
        "approved": approved,
        "rejected": rejected,
        "needs_revision": needs_revision,
        "classification_accuracy": round(classification_accuracy, 1),
        "class_correct_total": class_correct_total,
        "avg_confidence_rating": _safe_avg(
            query.filter(ReviewRecord.confidence_rating.isnot(None)),
            ReviewRecord.confidence_rating,
        ),
        "avg_quality_score": _safe_avg(
            query.filter(ReviewRecord.quality_score.isnot(None)),
            ReviewRecord.quality_score,
        ),
        "common_error_patterns": [
            {"from": p[0], "to": p[1], "count": p[2]}
            for p in error_patterns
        ],
    }


def _safe_avg(query, column) -> float:
    """Safely compute average, returning 0.0 if no rows."""
    result = query.with_entities(func.avg(column).label("avg")).first()
    val = result[0] if result and result[0] is not None else 0.0
    return round(float(val), 2)


# ── Reviewer Profile & Weight ──────────────────────────────────

def get_reviewer_profile(db: Session, user_id: str) -> Optional[Dict]:
    """Get reviewer profile as dict."""
    profile = db.query(ReviewerProfile).filter(
        ReviewerProfile.user_id == user_id
    ).first()
    if not profile:
        return None

    domain_exp = {}
    if profile.domain_expertise:
        try:
            domain_exp = json.loads(profile.domain_expertise)
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "user_id": str(profile.user_id),
        "total_reviews": profile.total_reviews or 0,
        "approved_count": profile.approved_count or 0,
        "rejected_count": profile.rejected_count or 0,
        "classification_accuracy": profile.classification_accuracy,
        "agreement_rate": profile.agreement_rate,
        "golden_sample_accuracy": profile.golden_sample_accuracy,
        "reviewer_level": profile.reviewer_level,
        "reviewer_weight": profile.reviewer_weight,
        "domain_expertise": domain_exp,
        "is_active": profile.is_active,
        "last_review_at": str(profile.last_review_at) if profile.last_review_at else None,
    }


def calculate_reviewer_weight(
    db: Session,
    user_id: str,
    golden_accuracy: Optional[float] = None,
    agreement_rate: Optional[float] = None,
    total_reviews: Optional[int] = None,
) -> float:
    """Calculate reviewer weight based on performance metrics.
    
    Formula:
        weight = 0.3 * golden_sample_accuracy + 0.3 * agreement_rate
               + 0.2 * min(total_reviews/100, 1.0) + 0.2 * domain_expertise_match
    """
    profile = db.query(ReviewerProfile).filter(
        ReviewerProfile.user_id == user_id
    ).first()

    ga = golden_accuracy or (profile.golden_sample_accuracy if profile else 0.0)
    ar = agreement_rate or (profile.agreement_rate if profile else 0.0)
    tr = total_reviews or (profile.total_reviews if profile else 0)

    ga = ga or 0.0
    ar = ar or 0.0
    tr = tr or 0

    experience_factor = min(tr / 100.0, 1.0)

    # Domain expertise match (simplified: use average of domain scores if available)
    domain_factor = 0.5
    if profile and profile.domain_expertise:
        try:
            scores = json.loads(profile.domain_expertise)
            if scores:
                domain_factor = sum(scores.values()) / len(scores)
        except (json.JSONDecodeError, TypeError):
            pass

    weight = 0.3 * ga + 0.3 * ar + 0.2 * experience_factor + 0.2 * domain_factor
    weight = max(0.1, min(weight, 1.0))  # clamp to [0.1, 1.0]

    # Update profile
    if profile:
        profile.reviewer_weight = weight
        profile.golden_sample_accuracy = ga
        profile.agreement_rate = ar
        db.commit()

    return round(weight, 3)


def update_all_reviewer_weights(db: Session, workspace_id: Optional[str] = None):
    """Batch update reviewer weights for all active reviewers."""
    query = db.query(ReviewerProfile).filter(ReviewerProfile.is_active == True)
    if workspace_id:
        query = query.filter(ReviewerProfile.workspace_id == workspace_id)

    for profile in query.all():
        # Calculate agreement rate by comparing with other reviewers
        agreement = _calculate_agreement_rate(db, profile.user_id, workspace_id)
        golden_acc = _calculate_golden_accuracy(db, profile.user_id, workspace_id)

        calculate_reviewer_weight(
            db, profile.user_id,
            golden_accuracy=golden_acc,
            agreement_rate=agreement,
            total_reviews=profile.total_reviews or 0,
        )


def _calculate_agreement_rate(db: Session, user_id: str, workspace_id: Optional[str] = None) -> float:
    """Calculate how often this reviewer agrees with others on the same context."""
    # Get contexts reviewed by this user
    own_reviews = db.query(ReviewRecord).filter(ReviewRecord.reviewer_id == user_id)
    if workspace_id:
        own_reviews = own_reviews.filter(ReviewRecord.workspace_id == workspace_id)

    context_ids = [r.context_id for r in own_reviews.all()]
    if not context_ids:
        return 0.0

    agreements = 0
    total_comparisons = 0

    for ctx_id in context_ids:
        own = db.query(ReviewRecord).filter(
            ReviewRecord.context_id == ctx_id,
            ReviewRecord.reviewer_id == user_id,
        ).first()
        if not own:
            continue

        others = db.query(ReviewRecord).filter(
            ReviewRecord.context_id == ctx_id,
            ReviewRecord.reviewer_id != user_id,
        ).all()

        for other in others:
            total_comparisons += 1
            if own.decision == other.decision:
                agreements += 1

    return agreements / total_comparisons if total_comparisons > 0 else 0.0


def _calculate_golden_accuracy(db: Session, user_id: str, workspace_id: Optional[str] = None) -> float:
    """Calculate accuracy on golden sample reviews."""
    query = db.query(ReviewRecord).filter(
        ReviewRecord.reviewer_id == user_id,
        ReviewRecord.is_golden_sample == True,
    )
    if workspace_id:
        query = query.filter(ReviewRecord.workspace_id == workspace_id)

    golden_reviews = query.all()
    if not golden_reviews:
        return 0.0

    # On golden samples, the "correct" classification_correct should be True
    # (golden samples have been pre-validated)
    correct = sum(1 for r in golden_reviews if r.classification_correct is True)
    return correct / len(golden_reviews)


# ── Golden Sample Management ──────────────────────────────────

def mark_golden_sample(db: Session, context_id: str, reviewer_id: str) -> ReviewRecord:
    """Mark a context's review record as a golden sample."""
    record = db.query(ReviewRecord).filter(
        ReviewRecord.context_id == context_id,
    ).first()
    if not record:
        raise ValueError("No review record found for this context")

    # Update context's auto_classification_correct
    ctx = db.query(ContextItem).filter(ContextItem.id == context_id).first()
    if ctx:
        ctx.auto_classification_correct = True

    record.is_golden_sample = True
    db.commit()
    db.refresh(record)

    log_audit(db, "mark_golden_sample", str(reviewer_id), context_id,
              {"action": "marked_as_golden_sample"})

    return record


def get_golden_samples(
    db: Session, workspace_id: Optional[str] = None, limit: int = 100
) -> List[ReviewRecord]:
    """Get list of golden sample review records."""
    query = db.query(ReviewRecord).filter(ReviewRecord.is_golden_sample == True)
    if workspace_id:
        query = query.filter(ReviewRecord.workspace_id == workspace_id)
    return query.order_by(ReviewRecord.created_at.desc()).limit(limit).all()


# ── Feedback Dataset Building ──────────────────────────────────

def build_training_dataset(
    db: Session,
    workspace_id: Optional[str] = None,
    name: Optional[str] = None,
    min_samples: int = 100,
    min_label_confidence: float = 0.7,
    train_test_split: float = 0.8,
    created_by: Optional[str] = None,
) -> Optional[FeedbackDataset]:
    """Build a training dataset from feedback data."""
    # Get validated labels
    labels = get_validated_labels(db, workspace_id, min_label_confidence, "domain")
    if len(labels) < min_samples:
        return None

    # Count domain distribution
    domain_dist = {}
    for label in labels:
        d = label.corrected_value
        domain_dist[d] = domain_dist.get(d, 0) + 1

    # Calculate current accuracy (before learning)
    all_reviews = db.query(ReviewRecord)
    if workspace_id:
        all_reviews = all_reviews.filter(ReviewRecord.workspace_id == workspace_id)
    total_class = all_reviews.filter(ReviewRecord.classification_correct.isnot(None)).count()
    correct_class = all_reviews.filter(ReviewRecord.classification_correct == True).count()
    accuracy_before = (correct_class / total_class * 100) if total_class > 0 else 0

    # Create dataset
    now = utcnow()
    version = f"v{now.strftime('%Y%m%d_%H%M')}"

    dataset = FeedbackDataset(
        name=name or f"train_{now.strftime('%YW%W')}",
        dataset_type="training",
        version=version,
        total_samples=len(labels),
        domain_distribution=json.dumps(domain_dist),
        class_accuracy_before=round(accuracy_before, 2),
        status="ready",
        snapshot_period_end=now,
        min_confidence_label=min_label_confidence,
        created_by=created_by,
    )
    if workspace_id:
        dataset.workspace_id = workspace_id

    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


# ── Anomaly Detection ─────────────────────────────────────────

def detect_feedback_anomalies(
    db: Session, workspace_id: Optional[str] = None,
) -> List[Dict]:
    """Detect anomalous feedback patterns (e.g., reviewer bias, speed anomalies)."""
    anomalies = []

    # Check for reviewers with unusually fast review times
    query = db.query(
        ReviewRecord.reviewer_id,
        func.avg(ReviewRecord.review_duration_seconds).label("avg_dur"),
        func.count(ReviewRecord.id).label("count"),
    ).filter(ReviewRecord.review_duration_seconds.isnot(None))
    if workspace_id:
        query = query.filter(ReviewRecord.workspace_id == workspace_id)

    fast_reviewers = query.group_by(ReviewRecord.reviewer_id).having(
        func.avg(ReviewRecord.review_duration_seconds) < 5,
        func.count(ReviewRecord.id) >= 10,
    ).all()

    for r in fast_reviewers:
        anomalies.append({
            "type": "fast_reviewer",
            "reviewer_id": str(r[0]),
            "avg_duration_seconds": round(float(r[1]), 1),
            "review_count": r[2],
            "message": f"Reviewer {r[0]} averages {r[1]:.1f}s per review (may indicate rushed reviews)",
        })

    # Check for reviewers with unusually low agreement
    profiles = db.query(ReviewerProfile).filter(
        ReviewerProfile.agreement_rate.isnot(None),
        ReviewerProfile.agreement_rate < 0.5,
        ReviewerProfile.total_reviews >= 10,
    )
    if workspace_id:
        profiles = profiles.filter(ReviewerProfile.workspace_id == workspace_id)

    for p in profiles.all():
        anomalies.append({
            "type": "low_agreement",
            "reviewer_id": str(p.user_id),
            "agreement_rate": p.agreement_rate,
            "message": f"Reviewer {p.user_id} has low agreement rate ({p.agreement_rate:.1%})",
        })

    return anomalies
