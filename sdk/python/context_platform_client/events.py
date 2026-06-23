"""Event handling for the Context Platform Python SDK."""
from typing import Optional, Callable, Dict, Any, List
import hmac
import hashlib
import json


class EventHandler:
    """Webhook event handler and signature verification."""

    EVENT_TYPES = [
        "context.created", "context.updated", "context.deleted",
        "context.status_changed", "context.confidence_changed",
        "relation.created", "relation.deleted",
        "entity.created", "entity.updated",
    ]

    def __init__(self, webhook_secret: str):
        self._secret = webhook_secret
        self._handlers: Dict[str, List[Callable]] = {}

    def on(self, event_type: str, handler: Callable):
        """Register an event handler."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """Verify HMAC-SHA256 webhook signature."""
        expected = hmac.new(
            self._secret.encode()[:32],
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def handle_event(self, event_type: str, payload: Dict[str, Any]):
        """Dispatch event to registered handlers."""
        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                handler(payload)
            except Exception:
                pass
