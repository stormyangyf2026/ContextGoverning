"""Tests for IntegrationAdapter — external authentication routing."""
import pytest
from app.services.adapter import get_adapter, IntegrationAdapter
from app.tests.conftest import make_workspace


class TestIntegrationAdapter:
    """Test the external integration authentication adapter."""

    def test_adapter_singleton(self):
        """get_adapter should return the same instance."""
        a1 = get_adapter()
        a2 = get_adapter()
        assert a1 is a2

    def test_adapter_is_integration_adapter(self):
        """get_adapter should return IntegrationAdapter instance."""
        a = get_adapter()
        assert isinstance(a, IntegrationAdapter)

    def test_verify_jwt_without_config(self, db):
        """_verify_jwt should return None when no JWT config exists."""
        adapter = get_adapter()
        result = adapter._verify_jwt("test_token", db)
        assert result is None

    def test_verify_custom_token_returns_none(self, db):
        """_verify_custom_token should return None (stub)."""
        adapter = get_adapter()
        result = adapter._verify_custom_token("test_token", db)
        assert result is None

    def test_api_key_auth_flow(self, db):
        """API key auth should find active (non-revoked) keys in database."""
        ws = make_workspace(db, name="Key Auth Workspace", slug="key_auth_ws")
        from app.models.api_key import ApiKey
        key_record = ApiKey(
            workspace_id=ws.id,
            key_hash="valid_test_api_key_hash32chars",
            key_prefix="cp_test",
            name="Test Key",
            is_revoked=False,
        )
        db.add(key_record)
        db.commit()
        db.refresh(key_record)

        found = db.query(ApiKey).filter(
            ApiKey.key_hash == "valid_test_api_key_hash32chars",
            ApiKey.is_revoked == False,
        ).first()
        assert found is not None
        assert str(found.workspace_id) == str(ws.id)

    def test_disabled_key_not_found(self, db):
        """Revoked API key should not be found as active."""
        ws = make_workspace(db, name="Disabled WS", slug="disabled_ws2")
        from app.models.api_key import ApiKey
        key_record = ApiKey(
            workspace_id=ws.id,
            key_hash="disabled_key_32chars_testing",
            key_prefix="cp_dis",
            name="Revoked Key",
            is_revoked=True,
        )
        db.add(key_record)
        db.commit()
        db.refresh(key_record)

        found = db.query(ApiKey).filter(
            ApiKey.key_hash == "disabled_key_32chars_testing",
            ApiKey.is_revoked == False,
        ).first()
        assert found is None
