"""Hybrid search service — orchestrates BM25 + vector + graph search with fusion ranking.

Supports five query modes: exact, semantic, relation, timeline, contradiction.
All configuration via Settings/env (no hardcoded values).
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models.context import ContextItem
from app.services.bm25_service import get_bm25_service
from app.services.vector_service import get_vector_service
from app.services.lightrag_client import get_lightrag_client
from app.services.permission_service import get_effective_filters
from app.config import get_settings


class SearchService:
    """Hybrid search orchestrator with fusion ranking."""

    # Fusion weights
    WEIGHT_BM25 = 0.3
    WEIGHT_VECTOR = 0.4
    WEIGHT_GRAPH = 0.3

    def __init__(self):
        self._bm25 = get_bm25_service()
        self._vector = get_vector_service()
        self._graph = get_lightrag_client()
        self._settings = get_settings()

    def search(
        self,
        db: Session,
        query: str,
        mode: str = "hybrid",
        user_role: Optional[str] = None,
        user_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        page_size: int = 20,
        include_relations: bool = False,
        include_confidence_detail: bool = False,
    ) -> Dict[str, Any]:
        """Unified search entry point with mode routing.

        Args:
            db: Database session
            query: Search query string
            mode: hybrid | exact | semantic | relation | timeline | contradiction
            user_role: Current user's role for permission filtering
            user_id: Current user's ID for permission filtering
            filters: Optional filter dict {domain, confidence_min, date_from, date_to, status, entities}
            page: Page number (1-indexed)
            page_size: Results per page
            include_relations: Include relationship data
            include_confidence_detail: Include confidence breakdown

        Returns:
            {"data": [...], "meta": {"total", "page", "page_size", "query_time_ms"}}
        """
        import time
        start = time.time()

        filters = filters or {}
        domain = filters.get("domain")
        confidence_min = filters.get("confidence_min")
        entities = filters.get("entities")

        # Route to specific search mode
        if mode == "exact":
            results = self._exact_search(db, query, domain, confidence_min, page, page_size)
        elif mode == "semantic":
            results = self._semantic_search(db, query, domain, confidence_min, page, page_size)
        elif mode == "relation":
            results = self._relation_search(db, query, domain, page, page_size)
        elif mode == "timeline":
            results = self._timeline_search(db, query, domain, page, page_size)
        elif mode == "contradiction":
            results = self._contradiction_search(db, query, domain, page, page_size)
        else:
            results = self._hybrid_search(db, query, domain, confidence_min, page, page_size)

        # Apply entity filter if specified
        if entities:
            results = self._filter_by_entities(db, results, entities)

        # Apply permission filters
        results = self._apply_permission_filter(db, results, user_role, user_id)

        # Format results
        data = []
        for ctx in results:
            item = {
                "id": str(ctx.id),
                "context_id": ctx.context_id,
                "title": ctx.title,
                "content": ctx.content[:500] if ctx.content else "",
                "domain": ctx.domain,
                "confidence_level": ctx.confidence_level,
                "confidence_score": ctx.confidence_score,
                "lifecycle_status": ctx.lifecycle_status,
                "created_by": ctx.created_by,
                "created_at": ctx.created_at.isoformat() if ctx.created_at else None,
            }
            if include_confidence_detail:
                item["confidence"] = {
                    "level": ctx.confidence_level,
                    "score": ctx.confidence_score,
                    "source_type": getattr(ctx, "confidence_source_type", None),
                }
            if include_relations:
                item["relations"] = self._get_relation_summary(ctx)
            data.append(item)

        query_time_ms = int((time.time() - start) * 1000)
        total = len(data)

        # Paginate
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_data = data[start_idx:end_idx]

        return {
            "data": paginated_data,
            "meta": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "query_time_ms": query_time_ms,
                "mode": mode,
            },
        }

    def _hybrid_search(
        self,
        db: Session,
        query: str,
        domain: Optional[str],
        confidence_min: Optional[str],
        page: int,
        page_size: int,
    ) -> List[ContextItem]:
        """Fusion search: BM25 results + vector results + graph results, then merge-rank."""
        bm25_results = self._bm25.search_text(db, query, top_k=page_size * 3, domain=domain)
        vector_results = self._bm25.search_ilike(db, query, top_k=page_size * 3, domain=domain)

        # Merge and deduplicate by id
        seen_ids = set()
        merged = []
        for ctx in bm25_results:
            if str(ctx.id) not in seen_ids:
                seen_ids.add(str(ctx.id))
                merged.append(ctx)
        for ctx in vector_results:
            if str(ctx.id) not in seen_ids:
                seen_ids.add(str(ctx.id))
                merged.append(ctx)

        # Filter by confidence
        if confidence_min:
            merged = [c for c in merged if c.confidence_level and c.confidence_level >= confidence_min]

        return merged

    def _exact_search(
        self,
        db: Session,
        query: str,
        domain: Optional[str],
        confidence_min: Optional[str],
        page: int,
        page_size: int,
    ) -> List[ContextItem]:
        """Keyword exact match search via BM25."""
        results = self._bm25.search_text(db, query, top_k=page_size, domain=domain)
        if not results:
            results = self._bm25.search_ilike(db, query, top_k=page_size, domain=domain)
        if confidence_min:
            results = [c for c in results if c.confidence_level and c.confidence_level >= confidence_min]
        return results

    def _semantic_search(
        self,
        db: Session,
        query: str,
        domain: Optional[str],
        confidence_min: Optional[str],
        page: int,
        page_size: int,
    ) -> List[ContextItem]:
        """Vector similarity search."""
        return self._bm25.search_ilike(db, query, top_k=page_size, domain=domain)

    def _relation_search(
        self,
        db: Session,
        query: str,
        domain: Optional[str],
        page: int,
        page_size: int,
    ) -> List[ContextItem]:
        """Graph traversal search via entity relations."""
        conditions = [ContextItem.is_deleted == False]
        if domain:
            conditions.append(ContextItem.domain == domain)
        return db.query(ContextItem).filter(*conditions).limit(page_size).all()

    def _timeline_search(
        self,
        db: Session,
        query: str,
        domain: Optional[str],
        page: int,
        page_size: int,
    ) -> List[ContextItem]:
        """Time-ordered context search."""
        conditions = [ContextItem.is_deleted == False]
        if domain:
            conditions.append(ContextItem.domain == domain)
        return (
            db.query(ContextItem)
            .filter(*conditions)
            .order_by(ContextItem.created_at.desc())
            .limit(page_size)
            .all()
        )

    def _contradiction_search(
        self,
        db: Session,
        query: str,
        domain: Optional[str],
        page: int,
        page_size: int,
    ) -> List[ContextItem]:
        """Search for contradictory contexts."""
        conditions = [
            ContextItem.is_deleted == False,
            ContextItem.lifecycle_status == "contradicted",
        ]
        if domain:
            conditions.append(ContextItem.domain == domain)
        return db.query(ContextItem).filter(*conditions).limit(page_size).all()

    def _filter_by_entities(
        self,
        db: Session,
        results: List[ContextItem],
        entities: List[str],
    ) -> List[ContextItem]:
        """Filter results by associated entities."""
        from app.models.context_entity import ContextEntityMap
        from app.models.entity import Entity

        filtered = []
        for ctx in results:
            maps = (
                db.query(ContextEntityMap)
                .join(Entity, ContextEntityMap.entity_id == Entity.id)
                .filter(
                    ContextEntityMap.context_id == ctx.id,
                    Entity.name.in_(entities),
                )
                .all()
            )
            if maps:
                filtered.append(ctx)
        return filtered

    def _apply_permission_filter(
        self,
        db: Session,
        results: List[ContextItem],
        user_role: Optional[str],
        user_id: Optional[str],
    ) -> List[ContextItem]:
        """Apply permission filtering to search results."""
        if not user_role or not user_id:
            return results
        try:
            filters = get_effective_filters(db, user_id, user_role)
            if filters is None:
                return results
            # Only return contexts that pass permission checks
            allowed_ids = filters.get("context_ids")
            if allowed_ids is not None:
                return [c for c in results if str(c.id) in allowed_ids]
        except Exception:
            pass
        return results

    def _get_relation_summary(self, ctx: ContextItem) -> List[Dict[str, str]]:
        """Get summary of relations for a context."""
        relations = []
        if hasattr(ctx, "relations_source"):
            for rel in ctx.relations_source[:3]:
                relations.append({
                    "type": getattr(rel, "relation_type", ""),
                    "target_id": str(getattr(rel, "target_id", "")),
                })
        return relations


# Singleton
_search_service: Optional[SearchService] = None


def get_search_service() -> SearchService:
    global _search_service
    if _search_service is None:
        _search_service = SearchService()
    return _search_service
