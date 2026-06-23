"""API Key authentication service — generate, verify, revoke API keys.

Provides API Key-based authentication for external integrations.
Keys are bcrypt-hashed for storage.
All configuration via Settings/env (no hardcoded values).
"""
import secrets
from typing import Optional, Dict
from sqlalchemy.orm import Session
from app.models.api_key import ApiKey
from app.core.security import hash_password, verify_password
from app.config import get_settings


class ApiKeyAuthService:
    """API Key authentication for external integrations."""

    def generate_api_key(
        self,
        db: Session,
        workspace_id: str,
        name: str,
    ) -> Dict[str, str]:
        """Generate a new API key for a workspace.

        Returns the plain text key (only shown once!).
        The key is stored as a bcrypt hash.
        """
        plain_key = f"cp_{secrets.token_hex(24)}"

        key_record = ApiKey(
            workspace_id=workspace_id,
            name=name,
            key_hash=hash_password(plain_key),
            is_active=True,
        )
        db.add(key_record)
        db.commit()

        return {
            "api_key": plain_key,
            "key_id": str(key_record.id),
            "name": name,
            "note": "Save this key — it will not be shown again.",
        }

    def verify_api_key(
        self,
        db: Session,
        api_key: str,
    ) -> Optional[str]:
        """Verify an API key and return workspace_id if valid."""
        from app.models.api_key import ApiKey

        # Query all active keys (verification via bcrypt is slow, but secure)
        keys = db.query(ApiKey).filter(ApiKey.is_active == True).all()
        for key_record in keys:
            try:
                if verify_password(api_key, key_record.key_hash):
                    return str(key_record.workspace_id)
            except Exception:
                continue
        return None

    def revoke_api_key(
        self,
        db: Session,
        key_id: str,
    ) -> bool:
        """Revoke (deactivate) an API key."""
        key_record = db.query(ApiKey).filter(ApiKey.id == key_id).first()
        if not key_record:
            return False
        key_record.is_active = False
        db.commit()
        return True

    def list_api_keys(
        self,
        db: Session,
        workspace_id: str,
    ) -> list:
        """List all API keys for a workspace (redacted)."""
        keys = (
            db.query(ApiKey)
            .filter(ApiKey.workspace_id == workspace_id, ApiKey.is_active == True)
            .all()
        )
        return [
            {
                "id": str(k.id),
                "name": k.name,
                "is_active": k.is_active,
                "created_at": k.created_at.isoformat() if k.created_at else None,
            }
            for k in keys
        ]


# Singleton
_api_key_auth: Optional[ApiKeyAuthService] = None


def get_api_key_auth() -> ApiKeyAuthService:
    global _api_key_auth
    if _api_key_auth is None:
        _api_key_auth = ApiKeyAuthService()
    return _api_key_auth
