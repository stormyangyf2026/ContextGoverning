"""Project knowledge base client — API clients for IMA, Feishu Drive, and other cloud drives.

Supports multiple knowledge base platforms through a unified interface.
"""
from typing import Optional, List, Dict
import httpx
from app.config import get_settings


class ProjectKbClient:
    """Unified client for project knowledge base APIs.

    Supports: IMA (ima.qq.com), Feishu Drive, generic cloud drives.
    """

    def __init__(
        self,
        platform: str = "ima",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        app_id: Optional[str] = None,
        app_secret: Optional[str] = None,
    ):
        settings = get_settings()
        self.platform = platform
        self.api_key = api_key
        self.base_url = base_url
        self.app_id = app_id
        self.app_secret = app_secret
        self._client = httpx.Client(timeout=settings.ima_api_timeout)

    def list_documents(self, space_id: Optional[str] = None) -> List[Dict]:
        """List available documents in the knowledge base."""
        if self.platform == "ima" and self.api_key:
            return self._list_ima_documents(space_id)
        elif self.platform == "feishu_drive" and self.app_id:
            return self._list_feishu_documents(space_id)
        return []

    def get_document(self, doc_id: str) -> Optional[Dict]:
        """Get a single document by ID."""
        if self.platform == "ima":
            return self._get_ima_document(doc_id)
        elif self.platform == "feishu_drive":
            return self._get_feishu_document(doc_id)
        return None

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Search documents by query."""
        if self.platform == "ima":
            return self._search_ima(query, limit)
        elif self.platform == "feishu_drive":
            return self._search_feishu(query, limit)
        return []

    # ---- IMA ----

    def _list_ima_documents(self, space_id: Optional[str] = None) -> List[Dict]:
        """IMA API: list documents in a knowledge base space."""
        url = f"{self.base_url}/v1/spaces/{space_id or 'default'}/documents"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            resp = self._client.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.json().get("data", [])
        except Exception:
            pass
        return []

    def _get_ima_document(self, doc_id: str) -> Optional[Dict]:
        """IMA API: get document content."""
        url = f"{self.base_url}/v1/documents/{doc_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            resp = self._client.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.json().get("data")
        except Exception:
            pass
        return None

    def _search_ima(self, query: str, limit: int = 10) -> List[Dict]:
        url = f"{self.base_url}/v1/search"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            resp = self._client.post(url, json={"query": query, "limit": limit}, headers=headers)
            if resp.status_code == 200:
                return resp.json().get("data", [])
        except Exception:
            pass
        return []

    # ---- Feishu Drive ----

    def _get_feishu_token(self) -> Optional[str]:
        """Get Feishu tenant access token."""
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        try:
            resp = self._client.post(url, json={
                "app_id": self.app_id,
                "app_secret": self.app_secret,
            })
            if resp.status_code == 200:
                return resp.json().get("tenant_access_token")
        except Exception:
            pass
        return None

    def _list_feishu_documents(self, space_id: Optional[str] = None) -> List[Dict]:
        token = self._get_feishu_token()
        if not token:
            return []
        url = "https://open.feishu.cn/open-apis/drive/v1/files"
        headers = {"Authorization": f"Bearer {token}"}
        try:
            resp = self._client.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.json().get("data", {}).get("files", [])
        except Exception:
            pass
        return []

    def _get_feishu_document(self, doc_id: str) -> Optional[Dict]:
        token = self._get_feishu_token()
        if not token:
            return None
        url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/raw_content"
        headers = {"Authorization": f"Bearer {token}"}
        try:
            resp = self._client.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.json().get("data", {})
        except Exception:
            pass
        return None

    def _search_feishu(self, query: str, limit: int = 10) -> List[Dict]:
        token = self._get_feishu_token()
        if not token:
            return []
        url = "https://open.feishu.cn/open-apis/search/v2/search"
        headers = {"Authorization": f"Bearer {token}"}
        try:
            resp = self._client.post(url, json={"query": query, "count": limit}, headers=headers)
            if resp.status_code == 200:
                return resp.json().get("data", {}).get("items", [])
        except Exception:
            pass
        return []
