"""Deduplication pipeline — detects and skips duplicate content.

Two strategies:
    1. Exact match: SHA256 content hash comparison
    2. Semantic match: Vector cosine similarity > threshold
"""
from typing import Optional
from sqlalchemy.orm import Session
import hashlib
from app.models.context import ContextItem
from app.config import get_settings

settings = get_settings()
DEFAULT_SIMILARITY_THRESHOLD = settings.dedup_similarity_threshold


def content_hash(content: str) -> str:
    """Generate SHA256 hash of content for exact dedup."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def check_exact_duplicate(db: Session, content: str) -> Optional[ContextItem]:
    """Check if content already exists by exact hash match."""
    h = content_hash(content)
    return (
        db.query(ContextItem)
        .filter(ContextItem.content_hash == h, ContextItem.is_deleted == False)
        .first()
    )


def check_semantic_duplicate(
    db: Session,
    content_vector,
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> Optional[ContextItem]:
    """Check if similar content already exists by vector similarity.

    Args:
        db: Database session
        content_vector: pgvector Vector object (1024-dim BGE-M3 embedding)
        threshold: Cosine similarity threshold (default 0.85)

    Returns:
        Existing ContextItem if similar content found, None otherwise.
    """
    if content_vector is None:
        return None

    # Find nearest neighbor via pgvector cosine distance
    similar = (
        db.query(ContextItem)
        .filter(ContextItem.content_vector.isnot(None), ContextItem.is_deleted == False)
        .order_by(ContextItem.content_vector.cosine_distance(content_vector))
        .first()
    )

    if similar is None:
        return None

    from numpy import dot
    from numpy.linalg import norm
    sim = dot(content_vector, similar.content_vector) / (
        norm(content_vector) * norm(similar.content_vector)
    )
    if sim > threshold:
        return similar
    return None


def dedup_check(
    db: Session,
    content: str,
    content_vector=None,
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> Optional[ContextItem]:
    """Full dedup check: exact first, then semantic.

    Returns existing ContextItem if duplicate found, None if content is new.
    """
    # Exact match first (fast)
    exact = check_exact_duplicate(db, content)
    if exact:
        return exact

    # Semantic match (slower, requires vector)
    if content_vector is not None:
        return check_semantic_duplicate(db, content_vector, threshold)

    return None
