"""Main client for the Context Platform Python SDK."""
from typing import Optional, List, Dict, Any
import httpx
from .models import Context, Entity, Relation, SearchResult


class ContextPlatformClient:
    """Python client for the Context Platform API.

    Usage:
        client = ContextPlatformClient("http://localhost:8000", api_key="cp_xxx")
        contexts = client.search("query text")
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self._base = base_url.rstrip("/")
        self._api_key = api_key
        self._client = httpx.Client(timeout=timeout)

    def _headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self._api_key:
            h["X-API-Key"] = self._api_key
        return h

    def _get(self, path: str) -> Any:
        r = self._client.get(f"{self._base}{path}", headers=self._headers())
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, data: Dict) -> Any:
        r = self._client.post(f"{self._base}{path}", json=data, headers=self._headers())
        r.raise_for_status()
        return r.json()

    # ── Contexts ─────────────────────────────────────────

    def create_context(self, **kwargs) -> Context:
        data = self._post("/api/v1/external/contexts", kwargs)
        return Context.from_dict(data)

    def get_context(self, context_id: str) -> Context:
        data = self._get(f"/api/v1/external/contexts/{context_id}")
        return Context.from_dict(data)

    def list_contexts(self, domain: Optional[str] = None) -> List[Context]:
        params = ""
        if domain:
            params = f"?domain={domain}"
        data = self._get(f"/api/v1/external/contexts{params}")
        if isinstance(data, list):
            return [Context.from_dict(c) for c in data]
        return [Context.from_dict(c) for c in data.get("data", [])]

    def update_context(self, context_id: str, **kwargs) -> Context:
        data = self._client.put(
            f"{self._base}/api/v1/external/contexts/{context_id}",
            json=kwargs, headers=self._headers()
        )
        data.raise_for_status()
        return Context.from_dict(data.json())

    def delete_context(self, context_id: str) -> bool:
        r = self._client.delete(
            f"{self._base}/api/v1/external/contexts/{context_id}",
            headers=self._headers()
        )
        return r.status_code == 200

    # ── Search ───────────────────────────────────────────

    def search(self, query: str, mode: str = "hybrid", **filters) -> List[SearchResult]:
        data = self._post("/api/v1/external/search", {
            "query": query,
            "mode": mode,
            "filters": filters,
        })
        return [SearchResult.from_dict(r) for r in data.get("data", [])]

    # ── Entities ─────────────────────────────────────────

    def list_entities(self) -> List[Entity]:
        data = self._get("/api/v1/external/entities")
        if isinstance(data, list):
            return [Entity.from_dict(e) for e in data]
        return [Entity.from_dict(e) for e in data.get("data", [])]

    def create_entity(self, name: str, entity_type: str = "other", **kwargs) -> Entity:
        data = self._post("/api/v1/external/entities", {"name": name, "type": entity_type, **kwargs})
        return Entity.from_dict(data)

    def get_entity(self, entity_id: str) -> Entity:
        data = self._get(f"/api/v1/external/entities/{entity_id}")
        return Entity.from_dict(data)

    def get_entity_graph(self, entity_id: str, depth: int = 2) -> Dict:
        return self._get(f"/api/v1/external/entities/{entity_id}/graph?depth={depth}")

    # ── Workspaces ───────────────────────────────────────

    def list_workspaces(self) -> List[Dict]:
        return self._get("/api/v1/external/workspaces")

    def create_workspace(self, name: str, **kwargs) -> Dict:
        return self._post("/api/v1/external/workspaces", {"name": name, **kwargs})

    # ── Metrics ──────────────────────────────────────────

    def get_overview(self) -> Dict:
        return self._get("/api/v1/metrics/overview")

    def get_freshness(self, days: int = 30) -> Dict:
        return self._get(f"/api/v1/metrics/freshness?days={days}")

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
