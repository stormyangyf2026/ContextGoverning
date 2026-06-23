"""Tests for Entity & Relation API endpoints."""
import pytest
from app.tests.conftest import make_context, make_entity


class TestEntityAPI:
    """Test entity CRUD endpoints."""

    def test_list_entities(self, client, db):
        """GET /api/v1/entities should return entity list."""
        make_entity(db, name="API实体A", type="customer", domain="customer")

        response = client.get("/api/v1/entities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_entity(self, client, db):
        """GET /api/v1/entities/{id} should return entity detail."""
        entity = make_entity(db, name="详情实体", type="customer", domain="customer")

        response = client.get(f"/api/v1/entities/{entity.id}")
        assert response.status_code == 200

    def test_create_entity(self, client):
        """POST /api/v1/entities should create entity."""
        payload = {
            "name": "新API实体",
            "type": "customer",
            "domain": "customer",
        }
        response = client.post("/api/v1/entities", json=payload)
        assert response.status_code == 200

    def test_entity_graph(self, client, db):
        """GET /api/v1/entities/graph should return graph data."""
        make_entity(db, name="图谱实体", type="customer", domain="customer")

        response = client.get("/api/v1/entities/graph?entity_name=图谱实体")
        assert response.status_code == 200


class TestUserAPI:
    """Test user management endpoints."""

    def test_list_users(self, client, db):
        """GET /api/v1/users should return user list."""
        response = client.get("/api/v1/users")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_user(self, client, db):
        """GET /api/v1/users/{id} should return user detail."""
        from app.models.user import User
        user = db.query(User).first()
        if user:
            response = client.get(f"/api/v1/users/{user.id}")
            assert response.status_code == 200


class TestMetricsAPI:
    """Test metrics endpoints."""

    def test_overview(self, client):
        """GET /api/v1/metrics/overview should return overview."""
        response = client.get("/api/v1/metrics/overview")
        assert response.status_code == 200
        assert "total_contexts" in response.json()

    def test_coverage(self, client):
        """GET /api/v1/metrics/coverage should return coverage."""
        response = client.get("/api/v1/metrics/coverage")
        assert response.status_code == 200

    def test_freshness(self, client):
        """GET /api/v1/metrics/freshness should return freshness."""
        response = client.get("/api/v1/metrics/freshness")
        assert response.status_code == 200

    def test_confidence_trends(self, client):
        """GET /api/v1/metrics/confidence-trends should return trends."""
        response = client.get("/api/v1/metrics/confidence-trends")
        assert response.status_code == 200


class TestConfigAPI:
    """Test config endpoints."""

    def test_get_config(self, client):
        """GET /api/v1/config should return config."""
        response = client.get("/api/v1/config")
        assert response.status_code == 200


class TestExternalAPI:
    """Test external API endpoints."""

    def test_external_health(self, client):
        """GET /api/v1/external/health should return healthy."""
        response = client.get("/api/v1/external/health")
        assert response.status_code == 200

    def test_external_health_metrics(self, client):
        """GET /api/v1/external/health/metrics should return metrics."""
        response = client.get("/api/v1/external/health/metrics")
        assert response.status_code == 200

    def test_external_search(self, client):
        """POST /api/v1/external/search should support search."""
        payload = {"query": "test", "mode": "hybrid"}
        response = client.post("/api/v1/external/search", json=payload)
        assert response.status_code == 200

    def test_external_contexts_list(self, client):
        """GET /api/v1/external/contexts should list contexts."""
        response = client.get("/api/v1/external/contexts")
        assert response.status_code == 200

    def test_external_entities(self, client):
        """GET /api/v1/external/entities should list entities."""
        response = client.get("/api/v1/external/entities")
        assert response.status_code == 200

    def test_external_whoami(self, client):
        """GET /api/v1/external/auth/whoami should return auth status."""
        response = client.get("/api/v1/external/auth/whoami")
        assert response.status_code == 200

    def test_external_workspaces(self, client):
        """GET /api/v1/external/workspaces should list workspaces."""
        response = client.get("/api/v1/external/workspaces")
        assert response.status_code == 200
