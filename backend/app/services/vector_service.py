"""pgvector vector index service — wrapper for PostgreSQL pgvector operations.

Provides vector similarity search using the pgvector extension.
All configuration via Settings/env (no hardcoded values).
"""
import struct
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.config import get_settings
from app.models._types import Vector
from app.models.context import ContextItem


class VectorService:
    """pgvector operations for context embedding similarity search."""

    def __init__(self):
        settings = get_settings()
        self._embedding_dim = settings.embedding_dimension

    def build_vector(self, embedding: List[float]) -> bytes:
        """Serialize a float list into pgvector binary wire format.

        pgvector binary format: 2 bytes unused + 2 bytes IEEE754 flag + 4 bytes dim + N*4 bytes floats
        """
        dim = len(embedding)
        float_bytes = struct.pack(f">{dim}f", *embedding)
        packed = struct.pack(f">HHI{4*dim}s", 0, 0, dim, float_bytes)
        return packed

    def parse_vector(self, binary: bytes, dim: Optional[int] = None) -> List[float]:
        """Parse pgvector binary wire format back to float list."""
        if binary is None or len(binary) < 8:
            return []
        if dim is None:
            # Read dim from the binary: bytes 4-8 are the dimension as int32
            read_dim = struct.unpack(">I", binary[4:8])[0]
            dim = read_dim
        expected_len = 8 + 4 * dim
        if len(binary) < expected_len:
            dim = min(dim, (len(binary) - 8) // 4)
        if dim <= 0:
            return []
        floats = struct.unpack(f">{dim}f", binary[8:8 + 4 * dim])
        return list(floats)

    def search_similar(
        self,
        db: Session,
        vector: List[float],
        top_k: int = 10,
        min_similarity: float = 0.7,
        domain: Optional[str] = None,
    ) -> List[ContextItem]:
        """Find contexts most similar to the given embedding vector.

        Uses pgvector cosine_distance for ranking (lower distance = more similar).
        Filters out deleted items and applies optional domain filter.
        """
        query = db.query(ContextItem).filter(
            ContextItem.content_vector.isnot(None),
            ContextItem.is_deleted == False,
        )

        if domain:
            query = query.filter(ContextItem.domain == domain)

        results = (
            query.order_by(
                ContextItem.content_vector.cosine_distance(vector)
            )
            .limit(top_k)
            .all()
        )

        return results

    def batch_index(
        self,
        db: Session,
        context_id: str,
        vector: List[float],
    ) -> None:
        """Update the embedding vector for a given context item."""
        ctx = db.query(ContextItem).filter(
            ContextItem.context_id == context_id,
            ContextItem.is_deleted == False,
        ).first()
        if ctx:
            ctx.content_vector = vector
            db.commit()


# Singleton accessor
_vector_service: Optional[VectorService] = None


def get_vector_service() -> VectorService:
    global _vector_service
    if _vector_service is None:
        _vector_service = VectorService()
    return _vector_service
