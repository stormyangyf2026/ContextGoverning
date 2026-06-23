"""Memory sync service — synchronizes context with Mem0 agent memory layer.

Implements the bridge between the platform's enterprise memory and Mem0's agent memory.
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.context import ContextItem
from app.services.confidence_service import can_agent_reference


class SyncService:
    """Bridge between Context Platform and Mem0 agent memory."""

    def __init__(self, mem0_client=None):
        """Initialize with an optional Mem0 client instance."""
        self.mem0 = mem0_client

    def sync_to_mem0(self, db: Session, context_ids: List[str], user_id: str) -> int:
        """Sync selected contexts to Mem0 for agent consumption.

        Only syncs contexts that are referenceable (L3-L5).

        Returns number of contexts synced.
        """
        synced = 0
        for ctx_id in context_ids:
            ctx = (
                db.query(ContextItem)
                .filter(ContextItem.context_id == ctx_id, ContextItem.is_deleted == False)
                .first()
            )
            if ctx is None:
                continue

            can_ref, _ = can_agent_reference(ctx.confidence_level)
            if not can_ref:
                continue

            if self.mem0:
                try:
                    self.mem0.add(
                        messages=[{
                            "role": "user",
                            "content": f"Context: {ctx.title}\n\n{ctx.content}",
                        }],
                        user_id=user_id,
                        metadata={
                            "context_id": ctx.context_id,
                            "confidence_level": ctx.confidence_level,
                            "domain": ctx.domain,
                        },
                    )
                except Exception:
                    continue

            synced += 1

        return synced

    def get_agent_contexts(
        self, db: Session, user_id: str, query: Optional[str] = None, limit: int = 10
    ) -> List[ContextItem]:
        """Get contexts suitable for agent consumption.

        Returns contexts with L3+ confidence that are active.
        """
        q = (
            db.query(ContextItem)
            .filter(
                ContextItem.is_deleted == False,
                ContextItem.lifecycle_status == "active",
                ContextItem.confidence_level.in_(["L3", "L4", "L5"]),
            )
            .order_by(ContextItem.confidence_score.desc())
        )

        if query:
            q = q.filter(
                ContextItem.title.ilike(f"%{query}%")
                | ContextItem.content.ilike(f"%{query}%")
            )

        return q.limit(limit).all()
