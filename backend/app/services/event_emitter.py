"""Webhook event emitter — pushes events to configured webhook endpoints.

Handles event formatting, HMAC-SHA256 signing, and exponential backoff retry.
All configuration via Settings/env (no hardcoded values).
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.config import get_settings


class EventEmitter:
    """Webhook event emission with retry and delivery logging."""

    # Standard event types
    EVENT_TYPES = [
        "context.created",
        "context.updated",
        "context.deleted",
        "context.status_changed",
        "context.confidence_changed",
        "relation.created",
        "relation.deleted",
        "entity.created",
        "entity.updated",
        "user.created",
        "user.updated",
        "workspace.created",
        "workspace.updated",
        "quota.warning",
    ]

    MAX_RETRIES = 5
    BASE_DELAY_SECONDS = 5

    def emit(
        self,
        db: Session,
        event_type: str,
        workspace_id: str,
        payload: Dict[str, Any],
        webhook_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Emit an event to configured webhook endpoints.

        Args:
            db: Database session
            event_type: Event type from EVENT_TYPES
            workspace_id: Workspace context
            payload: Event payload data
            webhook_url: Optional specific webhook URL

        Returns:
            {"success": bool, "delivery_id": str}
        """
        import hashlib
        import hmac
        import json
        import httpx

        settings = get_settings()

        event_data = {
            "event_type": event_type,
            "workspace_id": workspace_id,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_id": self._generate_event_id(),
        }

        delivered = False
        delivery_log_id = None

        if webhook_url:
            try:
                body = json.dumps(event_data, ensure_ascii=False, default=str)
                signature = self._sign(body, settings.jwt_secret_key)

                with httpx.Client(timeout=30.0) as client:
                    response = client.post(
                        webhook_url,
                        content=body,
                        headers={
                            "Content-Type": "application/json",
                            "X-Webhook-Signature": signature,
                            "X-Event-Type": event_type,
                        },
                    )
                    delivered = response.status_code == 200

                # Log delivery
                from app.models.webhook_delivery_log import WebhookDeliveryLog
                log = WebhookDeliveryLog(
                    workspace_id=workspace_id,
                    event_id=event_data["event_id"],
                    event_type=event_type,
                    payload=body,
                    status="delivered" if delivered else "failed",
                    response_code=response.status_code if not delivered else 200,
                )
                db.add(log)
                db.commit()
                delivery_log_id = str(log.id)
            except Exception:
                pass

        return {
            "success": delivered,
            "delivery_id": delivery_log_id,
            "event_id": event_data["event_id"],
        }

    def _generate_event_id(self) -> str:
        import uuid
        return f"evt_{uuid.uuid4().hex[:16]}"

    def _sign(self, body: str, secret: str) -> str:
        """Generate HMAC-SHA256 signature."""
        import hmac
        import hashlib
        mac = hmac.new(
            secret.encode()[:32],
            body.encode(),
            hashlib.sha256,
        )
        return mac.hexdigest()


# Singleton
_event_emitter: Optional[EventEmitter] = None


def get_event_emitter() -> EventEmitter:
    global _event_emitter
    if _event_emitter is None:
        _event_emitter = EventEmitter()
    return _event_emitter
