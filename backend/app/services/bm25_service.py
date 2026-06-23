"""BM25 full-text search service using PostgreSQL tsvector/tsquery.

Provides keyword-based full-text search with ranking.
All configuration via Settings/env (no hardcoded values).
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from app.models.context import ContextItem


class BM25Service:
    """PostgreSQL full-text search wrapper using tsvector/tsquery."""

    # Chinese text search configuration
    DEFAULT_CONFIG = "simple"

    def search_text(
        self,
        db: Session,
        query_str: str,
        top_k: int = 20,
        domain: Optional[str] = None,
    ) -> List[ContextItem]:
        """Perform full-text search on context content and title.

        Uses PostgreSQL ts_rank for relevance scoring.
        Falls back to ILIKE if no tsvector index is available.
        """
        ts_query = " & ".join(query_str.split())
        if not ts_query:
            return []

        # Build query with tsvector-based ranking
        conditions = [
            ContextItem.is_deleted == False,
        ]
        if domain:
            conditions.append(ContextItem.domain == domain)

        # Use PostgreSQL full-text search
        rank_expr = (
            func.ts_rank(
                func.to_tsvector(self.DEFAULT_CONFIG, func.coalesce(ContextItem.title, "") + " " + func.coalesce(ContextItem.content, "")),
                func.plainto_tsquery(self.DEFAULT_CONFIG, query_str),
            )
        )

        results = (
            db.query(ContextItem, rank_expr.label("rank"))
            .filter(*conditions)
            .filter(
                func.to_tsvector(self.DEFAULT_CONFIG, func.coalesce(ContextItem.title, "") + " " + func.coalesce(ContextItem.content, "")).op("@@")(
                    func.plainto_tsquery(self.DEFAULT_CONFIG, query_str)
                )
            )
            .order_by(rank_expr.desc())
            .limit(top_k)
            .all()
        )

        # Attach rank to each result item
        items = []
        for ctx, rank in results:
            ctx._bm25_rank = float(rank) if rank else 0.0
            items.append(ctx)

        return items

    def search_ilike(
        self,
        db: Session,
        query_str: str,
        top_k: int = 20,
        domain: Optional[str] = None,
    ) -> List[ContextItem]:
        """Fallback ILIKE search when tsvector is unavailable or yields no results."""
        conditions = [
            ContextItem.is_deleted == False,
        ]
        if domain:
            conditions.append(ContextItem.domain == domain)

        like_pattern = f"%{query_str}%"
        results = (
            db.query(ContextItem)
            .filter(*conditions)
            .filter(
                (ContextItem.title.ilike(like_pattern)) |
                (ContextItem.content.ilike(like_pattern))
            )
            .limit(top_k)
            .all()
        )
        return results


# Singleton
_bm25_service: Optional[BM25Service] = None


def get_bm25_service() -> BM25Service:
    global _bm25_service
    if _bm25_service is None:
        _bm25_service = BM25Service()
    return _bm25_service
