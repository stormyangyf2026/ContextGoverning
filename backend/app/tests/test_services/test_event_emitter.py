"""Tests for EventEmitter — webhook event emission with HMAC signing."""
import pytest
import json
from app.services.event_emitter import get_event_emitter, EventEmitter


class TestEventEmitter:
    """Test webhook event emission and HMAC signing."""

    def test_event_emitter_singleton(self):
        """get_event_emitter should return the same instance."""
        e1 = get_event_emitter()
        e2 = get_event_emitter()
        assert e1 is e2

    def test_event_types_list(self):
        """EventEmitter should define standard event types."""
        emitter = get_event_emitter()
        assert isinstance(emitter.EVENT_TYPES, list)
        assert len(emitter.EVENT_TYPES) == 14
        assert "context.created" in emitter.EVENT_TYPES
        assert "context.updated" in emitter.EVENT_TYPES
        assert "context.deleted" in emitter.EVENT_TYPES
        assert "context.status_changed" in emitter.EVENT_TYPES
        assert "context.confidence_changed" in emitter.EVENT_TYPES
        assert "relation.created" in emitter.EVENT_TYPES
        assert "relation.deleted" in emitter.EVENT_TYPES
        assert "entity.created" in emitter.EVENT_TYPES
        assert "entity.updated" in emitter.EVENT_TYPES
        assert "user.created" in emitter.EVENT_TYPES
        assert "user.updated" in emitter.EVENT_TYPES
        assert "workspace.created" in emitter.EVENT_TYPES
        assert "workspace.updated" in emitter.EVENT_TYPES
        assert "quota.warning" in emitter.EVENT_TYPES

    def test_emit_without_webhook_url(self, db):
        """emit without webhook_url should return success=False."""
        emitter = get_event_emitter()
        result = emitter.emit(
            db,
            event_type="context.created",
            workspace_id="00000000-0000-0000-0000-000000000001",
            payload={"test": "data"},
        )

        assert result["success"] is False
        assert "event_id" in result
        assert result["event_id"].startswith("evt_")

    def test_emit_event_id_format(self, db):
        """emit should generate valid event IDs."""
        emitter = get_event_emitter()
        result = emitter.emit(
            db,
            event_type="entity.updated",
            workspace_id="00000000-0000-0000-0000-000000000002",
            payload={"name": "测试"},
        )

        event_id = result["event_id"]
        assert event_id.startswith("evt_")
        assert len(event_id) == 20  # "evt_" + 16 hex chars

    def test_hmac_signing(self):
        """_sign should produce valid HMAC-SHA256 signatures."""
        emitter = get_event_emitter()
        body = json.dumps({"test": "payload"})
        secret = "test-secret-key-32chars-long!!"

        signature = emitter._sign(body, secret)
        assert isinstance(signature, str)
        assert len(signature) == 64  # SHA256 hex digest = 64 chars

    def test_hmac_signing_deterministic(self):
        """_sign should produce the same signature for same inputs."""
        emitter = get_event_emitter()
        body = json.dumps({"data": "test"})
        secret = "consistent-secret-key-32chars!"

        sig1 = emitter._sign(body, secret)
        sig2 = emitter._sign(body, secret)
        assert sig1 == sig2

    def test_hmac_signing_different_for_different_body(self):
        """_sign should produce different signatures for different bodies."""
        emitter = get_event_emitter()
        secret = "secret-key-for-testing-32chars"

        sig1 = emitter._sign(json.dumps({"a": 1}), secret)
        sig2 = emitter._sign(json.dumps({"b": 2}), secret)
        assert sig1 != sig2

    def test_emit_with_invalid_event_type(self, db):
        """emit should still work with custom event types."""
        emitter = get_event_emitter()
        result = emitter.emit(
            db,
            event_type="custom.event",
            workspace_id="00000000-0000-0000-0000-000000000003",
            payload={"custom": True},
        )

        assert result["success"] is False
        assert result["event_id"].startswith("evt_")

    def test_max_retries_constant(self):
        """MAX_RETRIES should be defined."""
        assert EventEmitter.MAX_RETRIES == 5

    def test_base_delay_constant(self):
        """BASE_DELAY_SECONDS should be defined."""
        assert EventEmitter.BASE_DELAY_SECONDS == 5

    def test_emit_generates_unique_event_ids(self, db):
        """Each emit call should generate unique event IDs."""
        emitter = get_event_emitter()
        ids = set()
        for i in range(5):
            result = emitter.emit(
                db,
                event_type="context.created",
                workspace_id="00000000-0000-0000-0000-000000000001",
                payload={"index": i},
            )
            ids.add(result["event_id"])

        assert len(ids) == 5  # All unique
