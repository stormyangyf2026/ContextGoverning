"""Feishu Bot — sends messages and notifications via Feishu Bot webhook."""
import httpx
from typing import Optional, List, Dict
from app.config import get_settings


class FeishuBot:
    """Send messages via Feishu bot webhook."""

    def __init__(self, webhook_url: str):
        settings = get_settings()
        self.webhook_url = webhook_url
        self._client = httpx.Client(timeout=settings.feishu_bot_timeout)

    def send_text(self, text: str) -> bool:
        """Send a plain text message."""
        return self._send({"msg_type": "text", "content": {"text": text}})

    def send_card(self, title: str, elements: List[Dict]) -> bool:
        """Send an interactive card message."""
        card = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": title},
                    "template": "blue",
                },
                "elements": elements,
            },
        }
        return self._send(card)

    def send_context_notification(
        self, title: str, content: str, url: Optional[str] = None
    ) -> bool:
        """Send a context update notification card."""
        elements = [
            {"tag": "markdown", "content": content},
        ]
        if url:
            elements.append({
                "tag": "action",
                "actions": [{
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "查看详情"},
                    "url": url,
                    "type": "default",
                }],
            })
        return self.send_card(f"📋 {title}", elements)

    def _send(self, payload: Dict) -> bool:
        try:
            resp = self._client.post(self.webhook_url, json=payload)
            return resp.status_code == 200
        except Exception:
            return False
