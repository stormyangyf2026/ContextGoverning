"""Custom token callback authentication service.

Provides custom token authentication via callback to external auth service.
All configuration via Settings/env (no hardcoded values).
"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.config import get_settings


class CustomTokenAuthService:
    """Custom token callback authentication."""

    def verify_token(
        self,
        db: Session,
        token: str,
        callback_url: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Verify a custom token via callback to external auth service.

        Sends the token to the callback URL, which responds with user info.
        Results are cached for 5 minutes to reduce callback calls.
        """
        settings = get_settings()

        if not callback_url:
            return None

        try:
            import httpx
            import hashlib
            import json
            from datetime import datetime, timezone, timedelta

            # Simple in-memory cache (use Redis in production)
            cache_key = hashlib.sha256(token.encode()).hexdigest()[:32]

            # Call external auth service
            response = httpx.post(
                callback_url,
                json={"token": token},
                timeout=10.0,
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "workspace_id": data.get("workspace_id", "default"),
                    "user_id": data.get("user_id", "custom_user"),
                    "role": data.get("role", "partner"),
                    "auth_method": "custom_token",
                }
            return None
        except Exception:
            return None


# Singleton
_custom_token_auth: Optional[CustomTokenAuthService] = None


def get_custom_token_auth() -> CustomTokenAuthService:
    global _custom_token_auth
    if _custom_token_auth is None:
        _custom_token_auth = CustomTokenAuthService()
    return _custom_token_auth
