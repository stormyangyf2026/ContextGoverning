"""RLHF confidence calibration service — calibrate confidence parameters from human feedback."""
import json
import statistics
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.review_feedback import ReviewRecord, ReviewerProfile
from app.models.context import ContextItem


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Initial Confidence Map Calibration ─────────────────────────

def calibrate_initial_confidence(
    db: Session,
    workspace_id: Optional[str] = None,
    learning_rate: float = 0.2,
) -> Dict[str, Tuple[str, float]]:
    """Calibrate the INITIAL_CONFIDENCE_MAP based on reviewer ratings.

    For each source_type, compare the system's initial confidence score
    with the average reviewer confidence rating, then adjust.

    Returns: dict of {source_type: (level, score)} with suggested updates.
    """
    # Get reviews grouped by context's confidence_source_type
    results = (
        db.query(
            ContextItem.confidence_source_type,
            func.avg(ReviewRecord.confidence_rating).label("avg_rating"),
            func.count(ReviewRecord.id).label("count"),
        )
        .join(ReviewRecord, ReviewRecord.context_id == ContextItem.id)
        .filter(
            ReviewRecord.confidence_rating.isnot(None),
            ContextItem.confidence_source_type.isnot(None),
        )
    )
    if workspace_id:
        results = results.filter(ReviewRecord.workspace_id == workspace_id)

    results = results.group_by(ContextItem.confidence_source_type).having(
        func.count(ReviewRecord.id) >= 5,
    ).all()

    # Build suggested updates
    suggestions = {}
    for row in results:
        source_type = row[0]
        avg_rating = float(row[1]) if row[1] else 0
        count = int(row[2])

        # Convert 1-5 rating to 0-1 score
        feedback_score = avg_rating / 5.0

        # Get current initial score
        from app.services.confidence_service import get_initial_confidence
        current_level, current_score = get_initial_confidence(source_type)

        # Calibrate: calibrated = current + λ * (feedback - current)
        calibrated_score = current_score + learning_rate * (feedback_score - current_score)
        calibrated_score = max(0.0, min(calibrated_score, 1.0))

        from app.services.confidence_service import resolve_level
        calibrated_level = resolve_level(calibrated_score)

        deviation = abs(calibrated_score - current_score)

        suggestions[source_type] = {
            "current": (current_level, current_score),
            "suggested": (calibrated_level, round(calibrated_score, 3)),
            "avg_feedback_rating": round(avg_rating, 1),
            "sample_count": count,
            "deviation": round(deviation, 3),
            "significant": deviation > 0.05,
        }

    return suggestions


# ── Weighted Confidence Calculation ────────────────────────────

def calculate_weighted_confidence(
    db: Session, context_id: str,
) -> Optional[Dict]:
    """Calculate weighted confidence considering multiple reviewer ratings.

    Returns: {
        "weighted_score": float,
        "weighted_level": str,
        "individual_ratings": [...],
        "reviewer_count": int,
    }
    """
    # Get all review records for this context with confidence ratings
    reviews = (
        db.query(ReviewRecord, ReviewerProfile)
        .outerjoin(ReviewerProfile, ReviewRecord.reviewer_id == ReviewerProfile.user_id)
        .filter(
            ReviewRecord.context_id == context_id,
            ReviewRecord.confidence_rating.isnot(None),
        )
        .all()
    )

    if not reviews:
        return None

    total_weight = 0.0
    weighted_sum = 0.0
    individual = []

    for review, profile in reviews:
        weight = profile.reviewer_weight if profile else 0.5
        rating = review.confidence_rating or 3  # default neutral
        weighted_sum += weight * rating
        total_weight += weight
        individual.append({
            "reviewer_id": str(review.reviewer_id),
            "rating": rating,
            "weight": weight,
            "adjustment": review.confidence_adjustment,
        })

    # Convert to 0-1 score
    avg_rating = weighted_sum / total_weight if total_weight > 0 else 3.0
    weighted_score = avg_rating / 5.0

    from app.services.confidence_service import resolve_level

    return {
        "weighted_score": round(weighted_score, 3),
        "weighted_level": resolve_level(weighted_score),
        "individual_ratings": individual,
        "reviewer_count": len(reviews),
    }


# ── Review Upgrade Calibration ─────────────────────────────────

def calibrate_review_upgrade(
    db: Session,
    workspace_id: Optional[str] = None,
) -> Dict:
    """Calibrate the review_upgrade() target based on feedback.

    Currently hardcoded to L3/0.78. This analyzes actual review outcomes
    to suggest a data-driven target.
    """
    # Get approved reviews with confidence ratings
    query = (
        db.query(
            func.avg(ReviewRecord.adjusted_confidence_score).label("avg_score"),
            func.count(ReviewRecord.id).label("count"),
        )
        .filter(
            ReviewRecord.decision == "approved",
            ReviewRecord.adjusted_confidence_score.isnot(None),
        )
    )
    if workspace_id:
        query = query.filter(ReviewRecord.workspace_id == workspace_id)

    result = query.first()
    avg_score = float(result[0]) if result and result[0] else 0.78
    count = int(result[1]) if result and result[1] else 0

    from app.services.confidence_service import resolve_level

    return {
        "current": {"level": "L3", "score": 0.78},
        "suggested": {
            "level": resolve_level(avg_score),
            "score": round(avg_score, 3),
        },
        "sample_count": count,
        "significant": abs(avg_score - 0.78) > 0.05,
    }


# ── Confidence Drift Detection ─────────────────────────────────

def detect_confidence_drift(
    db: Session,
    workspace_id: Optional[str] = None,
    period_days: int = 30,
    drift_threshold: float = 0.1,
) -> List[Dict]:
    """Detect confidence drift: growing gap between system scores and reviewer ratings.

    If the gap is widening over time, it signals that the confidence engine
    needs recalibration.
    """
    from sqlalchemy import text

    # This is a simplified drift detection.
    # For production, use time-series analysis comparing weekly score gaps.
    query = db.query(
        func.date_trunc("week", ReviewRecord.created_at).label("week"),
        func.avg(ReviewRecord.confidence_rating).label("avg_rating"),
        func.avg(ReviewRecord.adjusted_confidence_score).label("avg_adjusted"),
        func.count(ReviewRecord.id).label("count"),
    ).filter(
        ReviewRecord.confidence_rating.isnot(None),
        ReviewRecord.adjusted_confidence_score.isnot(None),
    )
    if workspace_id:
        query = query.filter(ReviewRecord.workspace_id == workspace_id)

    weekly = query.group_by(func.date_trunc("week", ReviewRecord.created_at)).order_by(
        func.date_trunc("week", ReviewRecord.created_at).desc()
    ).limit(8).all()

    drifts = []
    prev_gap = None

    for week in reversed(weekly):
        if week[3] < 5:  # skip weeks with too few samples
            continue

        avg_rating = float(week[1]) / 5.0 if week[1] else 0.5
        avg_adjusted = float(week[2]) if week[2] else avg_rating
        gap = abs(avg_adjusted - avg_rating)

        if prev_gap is not None and (gap - prev_gap) > drift_threshold:
            drifts.append({
                "week": str(week[0]),
                "avg_reviewer_score": round(avg_rating, 3),
                "avg_system_score": round(avg_adjusted, 3),
                "gap": round(gap, 3),
                "gap_change": round(gap - prev_gap, 3),
                "alert": f"Confidence gap widening: {gap - prev_gap:.3f} increase",
            })

        prev_gap = gap

    return drifts


# ── Weighted Vote Aggregation ──────────────────────────────────

def aggregate_weighted_votes(
    db: Session, context_id: str,
) -> Dict:
    """Aggregate weighted reviewer votes for a context.

    Useful for contexts reviewed by multiple reviewers with different weights.
    """
    reviews = (
        db.query(ReviewRecord, ReviewerProfile)
        .outerjoin(ReviewerProfile, ReviewRecord.reviewer_id == ReviewerProfile.user_id)
        .filter(ReviewRecord.context_id == context_id)
        .all()
    )

    if not reviews:
        return {"context_id": str(context_id), "consensus": "no_reviews", "total_reviewers": 0}

    # Weighted decision vote
    decision_scores = {"approved": 0.0, "rejected": 0.0, "needs_revision": 0.0}
    total_weight = 0.0

    for review, profile in reviews:
        weight = profile.reviewer_weight if profile else 0.5
        decision_scores[review.decision] = decision_scores.get(review.decision, 0.0) + weight
        total_weight += weight

    # Normalize
    if total_weight > 0:
        for k in decision_scores:
            decision_scores[k] = round(decision_scores[k] / total_weight, 3)

    # Determine consensus
    max_decision = max(decision_scores, key=decision_scores.get)
    consensus = max_decision if decision_scores[max_decision] >= 0.5 else "no_consensus"

    return {
        "context_id": str(context_id),
        "consensus": consensus,
        "decision_scores": decision_scores,
        "total_weight": round(total_weight, 3),
        "total_reviewers": len(reviews),
    }
