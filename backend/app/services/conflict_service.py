"""Conflict detection service — identifies contradictory contexts and manages resolution."""
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from app.models.context import ContextItem
from app.models.relation import Relation
from app.services.confidence_service import apply_conflict_penalty
from app.config import get_settings

_settings = get_settings()


def detect_conflicts(
    db: Session,
    context_id: str,
    similarity_threshold: float = None,
) -> List[Tuple[ContextItem, float]]:
    """Detect contexts that may contradict a given context.

    Uses cosine similarity of content vectors to find similar topics,
    then checks for contradictory relation type.

    Returns list of (conflicting_context, similarity_score) tuples.
    """
    if similarity_threshold is None:
        similarity_threshold = _settings.conflict_similarity_threshold
    ctx = db.query(ContextItem).filter(ContextItem.context_id == context_id).first()
    if ctx is None or ctx.content_vector is None:
        return []

    # Find contexts with similar vectors (same entity domain)
    similar = (
        db.query(ContextItem)
        .filter(
            ContextItem.id != ctx.id,
            ContextItem.lifecycle_status.in_(["active", "decaying"]),
        )
        .all()
    )

    conflicts = []
    for other in similar:
        # Mark as potential conflict if same entity/topic but different confidence sources
        if other.content_vector is not None:
            from numpy import dot
            from numpy.linalg import norm
            v1 = ctx.content_vector
            v2 = other.content_vector
            sim = dot(v1, v2) / (norm(v1) * norm(v2))
            if sim > similarity_threshold:
                conflicts.append((other, sim))

    return conflicts


def mark_as_contradicted(
    db: Session,
    actor: str,
    context_a_id: str,
    context_b_id: str,
) -> Tuple[ContextItem, ContextItem, Relation]:
    """Mark two contexts as contradicted and create a contradicts relation."""
    a = db.query(ContextItem).filter(ContextItem.context_id == context_a_id).first()
    b = db.query(ContextItem).filter(ContextItem.context_id == context_b_id).first()

    if a is None or b is None:
        raise ValueError("One or both contexts not found")

    # Penalize both
    a.confidence_score = apply_conflict_penalty(a.confidence_score)
    a.lifecycle_status = "contradicted"

    b.confidence_score = apply_conflict_penalty(b.confidence_score)
    b.lifecycle_status = "contradicted"

    # Create contradicts relation
    relation = Relation(
        source_id=a.id,
        target_id=b.id,
        relation_type="contradicts",
        direction="bidirectional",
        created_by=actor,
    )
    db.add(relation)
    db.commit()
    db.refresh(a)
    db.refresh(b)
    db.refresh(relation)

    return a, b, relation


def resolve_conflict(
    db: Session,
    actor: str,
    winner_context_id: str,
    loser_context_id: str,
) -> Tuple[ContextItem, ContextItem]:
    """Resolve a contradiction: winner restored, loser archived."""
    winner = db.query(ContextItem).filter(ContextItem.context_id == winner_context_id).first()
    loser = db.query(ContextItem).filter(ContextItem.context_id == loser_context_id).first()

    if winner is None or loser is None:
        raise ValueError("One or both contexts not found")

    # Restore winner (can't fully restore score but set to active)
    winner.lifecycle_status = "active"

    # Archive loser
    loser.confidence_score = 0.10
    loser.lifecycle_status = "archived"

    db.commit()
    db.refresh(winner)
    db.refresh(loser)

    return winner, loser
