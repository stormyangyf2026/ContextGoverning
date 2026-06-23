"""Feishu API client — Lark/Feishu Open API integration."""
from typing import Optional, List, Dict
import httpx
from app.config import get_settings


class FeishuClient:
    """Client for Feishu (Lark) Open API."""

    def __init__(self, app_id: str, app_secret: str):
        settings = get_settings()
        self.app_id = app_id
        self.app_secret = app_secret
        self._client = httpx.Client(timeout=settings.feishu_api_timeout)
        self._token: Optional[str] = None

    def _get_token(self) -> Optional[str]:
        if self._token:
            return self._token
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        try:
            resp = self._client.post(url, json={
                "app_id": self.app_id,
                "app_secret": self.app_secret,
            })
            if resp.status_code == 200:
                self._token = resp.json().get("tenant_access_token")
                return self._token
        except Exception:
            pass
        return None

    def _headers(self) -> dict:
        token = self._get_token()
        return {"Authorization": f"Bearer {token}"} if token else {}

    def list_documents(self, folder_token: Optional[str] = None) -> List[Dict]:
        """List documents in a Feishu Drive folder."""
        url = "https://open.feishu.cn/open-apis/drive/v1/files"
        params = {"page_size": 100}
        if folder_token:
            params["folder_token"] = folder_token
        try:
            resp = self._client.get(url, headers=self._headers(), params=params)
            if resp.status_code == 200:
                return resp.json().get("data", {}).get("files", [])
        except Exception:
            pass
        return []

    def get_document_content(self, doc_token: str) -> Optional[str]:
        """Get plain text content of a Feishu Doc."""
        url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_token}/raw_content"
        try:
            resp = self._client.get(url, headers=self._headers())
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                return data.get("content", "")
        except Exception:
            pass
        return None

    def list_group_messages(self, chat_id: str, limit: int = 100) -> List[Dict]:
        """Get recent messages from a group chat."""
        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        params = {
            "receive_id_type": "chat_id",
            "receive_id": chat_id,
            "page_size": min(limit, 100),
        }
        try:
            resp = self._client.get(url, headers=self._headers(), params=params)
            if resp.status_code == 200:
                return resp.json().get("data", {}).get("items", [])
        except Exception:
            pass
        return []

    def get_message_content(self, message_id: str) -> Optional[str]:
        """Get the text content of a specific message."""
        url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}"
        try:
            resp = self._client.get(url, headers=self._headers())
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                items = data.get("items", [])
                for item in items:
                    if item.get("msg_type") == "text":
                        return item.get("body", {}).get("content", "")
        except Exception:
            pass
        return None
