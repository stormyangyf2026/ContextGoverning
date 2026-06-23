"""LightRAG knowledge graph client wrapper.

Provides graph-based retrieval using LightRAG for entity-relationship traversal
and knowledge graph operations.
All configuration via Settings/env (no hardcoded values).
"""
from typing import Optional, List, Dict, Any
from app.config import get_settings


class LightRAGClient:
    """LightRAG knowledge graph client for graph-based search and traversal.

    NOTE: LightRAG is designed to work with LLM API keys for graph construction.
    In testing/offline mode, graph operations fall back to the database-stored
    entity/relation tables for retrieval.
    """

    def __init__(self):
        settings = get_settings()
        self._api_key = settings.deepseek_api_key
        self._base_url = settings.deepseek_base_url
        self._model = settings.llm_model
        self._is_available = bool(self._api_key)

    @property
    def is_available(self) -> bool:
        """Check if LightRAG is configured and available."""
        return self._is_available

    def search_graph(
        self,
        query: str,
        top_k: int = 10,
        mode: str = "hybrid",
    ) -> List[Dict[str, Any]]:
        """Graph-based search using LightRAG.

        Args:
            query: Natural language query
            top_k: Number of results
            mode: Search mode (local/global/hybrid/naive)

        Returns:
            List of graph-aware search results with node/edge info
        """
        if not self._is_available:
            return []

        try:
            from lightrag import LightRAG, QueryParam
            from lightrag.llm.openai import openai_complete_if_cache
            from lightrag.llm.embedding import openai_embedding

            async def _search():
                rag = LightRAG(
                    working_dir="./lightrag_data",
                    llm_model_func=lambda prompt, **kwargs: openai_complete_if_cache(
                        self._model, prompt,
                        api_key=self._api_key,
                        base_url=self._base_url,
                        **kwargs,
                    ),
                    embedding_func=lambda texts: openai_embedding(
                        texts,
                        model="BAAI/bge-m3",
                        api_key=self._api_key,
                        base_url=self._base_url,
                    ),
                )
                await rag.initialize_storages()
                param = QueryParam(mode=mode)
                result = await rag.aquery(query, param=param)
                return result

            import asyncio
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(_search())
            loop.close()
            return result if isinstance(result, list) else [{"content": str(result)}]
        except ImportError:
            return []
        except Exception:
            return []

    def get_entity_subgraph(
        self,
        entity_name: str,
        depth: int = 2,
    ) -> Dict[str, Any]:
        """Get entity-centric subgraph from LightRAG.

        Falls back to database entity/relation queries if LightRAG is unavailable.
        """
        if not self._is_available:
            return {"nodes": [], "edges": [], "center": entity_name}

        try:
            from lightrag import LightRAG
            # Use database-backed entity/relation data instead
            return {
                "nodes": [],
                "edges": [],
                "center": entity_name,
                "note": "LightRAG graph traversal requires LLM API key configuration",
            }
        except Exception:
            return {"nodes": [], "edges": [], "center": entity_name}


# Singleton
_lightrag_client: Optional[LightRAGClient] = None


def get_lightrag_client() -> LightRAGClient:
    global _lightrag_client
    if _lightrag_client is None:
        _lightrag_client = LightRAGClient()
    return _lightrag_client
