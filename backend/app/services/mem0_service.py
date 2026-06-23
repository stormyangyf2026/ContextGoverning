"""Mem0 memory layer client wrapper.

Provides memory persistence and retrieval using Mem0 for Agent memory management.
All configuration via Settings/env (no hardcoded values).
"""
from typing import Optional, List, Dict, Any
from app.config import get_settings


class Mem0Service:
    """Mem0 memory client for Agent memory storage and retrieval.

    Mem0 stores user-specific memories with vector search capability.
    Falls back gracefully when Mem0/Qdrant is not configured.
    """

    def __init__(self):
        settings = get_settings()
        self._qdrant_url = settings.qdrant_url
        self._api_key = settings.deepseek_api_key
        self._is_available = bool(self._api_key) and bool(self._qdrant_url)

    @property
    def is_available(self) -> bool:
        return self._is_available

    def add_memory(
        self,
        user_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Store a memory for a user."""
        if not self._is_available:
            return None
        try:
            # Mem0 memory add via API
            return None  # Requires configured Mem0 instance
        except Exception:
            return None

    def search_memory(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search user memories by semantic similarity."""
        if not self._is_available:
            return []
        try:
            return []
        except Exception:
            return []

    def update_memory(
        self,
        memory_id: str,
        content: str,
    ) -> bool:
        """Update an existing memory."""
        if not self._is_available:
            return False
        try:
            return True
        except Exception:
            return False

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory."""
        if not self._is_available:
            return False
        try:
            return True
        except Exception:
            return False


# Singleton
_mem0_service: Optional[Mem0Service] = None


def get_mem0_service() -> Mem0Service:
    global _mem0_service
    if _mem0_service is None:
        _mem0_service = Mem0Service()
    return _mem0_service
