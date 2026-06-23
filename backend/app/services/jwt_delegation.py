"""JWT delegation authentication service.

Provides JWT-based authentication delegation, JWKS key retrieval,
and claim mapping for external identity providers.
All configuration via Settings/env (no hardcoded values).
"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.config import get_settings


class JwtDelegationService:
    """JWT delegation authentication for external identity providers."""

    def verify_token(
        self,
        db: Session,
        token: str,
    ) -> Optional[Dict[str, Any]]:
        """Verify a delegated JWT token.

        Retrieves JWKS from configured endpoint, verifies token,
        applies claim mapping to extract workspace_id and role.
        """
        settings = get_settings()

        from app.models.jwt_config import JwtConfig
        jwt_config = db.query(JwtConfig).first()
        if not jwt_config:
            return None

        try:
            from jose import jwt, jwk, exceptions as jose_exceptions

            # Get JWKS
            jwks_url = getattr(jwt_config, "jwks_url", None)
            if not jwks_url:
                # Use HMAC verification with app secret
                payload = jwt.decode(
                    token,
                    settings.jwt_secret_key,
                    algorithms=[settings.jwt_algorithm],
                )
            else:
                # Fetch JWKS and verify
                import httpx
                response = httpx.get(jwks_url, timeout=10.0)
                keys = response.json()
                payload = jwt.decode(token, keys, algorithms=["RS256"])

            # Apply claim mapping
            workspace_id = payload.get("workspace_id") or payload.get("sub")
            role = payload.get("role", "partner")
            user_id = payload.get("sub", "delegated_user")

            return {
                "workspace_id": workspace_id,
                "user_id": user_id,
                "role": role,
                "auth_method": "jwt_delegation",
            }
        except Exception:
            return None

    def get_default_role(self, db: Session, workspace_id: str) -> str:
        """Get the default role for a workspace when no role is specified."""
        return "partner"


# Singleton
_jwt_delegation: Optional[JwtDelegationService] = None


def get_jwt_delegation() -> JwtDelegationService:
    global _jwt_delegation
    if _jwt_delegation is None:
        _jwt_delegation = JwtDelegationService()
    return _jwt_delegation
