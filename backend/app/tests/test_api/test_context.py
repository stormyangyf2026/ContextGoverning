"""Tests for Context API endpoints."""
import pytest
from app.tests.conftest import make_context


class TestContextAPI:
    """Test the v1 context CRUD endpoints."""

    def test_list_contexts(self, client):
        """GET /api/v1/contexts should return list of contexts."""
        response = client.get("/api/v1/contexts")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_contexts_with_filters(self, client):
        """List contexts with domain filter should work."""
        response = client.get("/api/v1/contexts?domain=operations")
        assert response.status_code == 200

    def test_list_contexts_with_pagination(self, client):
        """List contexts should support skip and limit."""
        response = client.get("/api/v1/contexts?skip=0&limit=10")
        assert response.status_code == 200

    def test_get_context_not_found(self, client):
        """GET /api/v1/contexts/{id} should return 404 for nonexistent."""
        response = client.get("/api/v1/contexts/nonexistent-id")
        assert response.status_code == 404

    def test_get_context(self, client, db):
        """GET /api/v1/contexts/{id} should return context."""
        ctx = make_context(db, context_id="ctx_api_test01", title="API测试",
                          content="API测试内容")
        response = client.get(f"/api/v1/contexts/{ctx.context_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["context_id"] == "ctx_api_test01"

    def test_create_context(self, client):
        """POST /api/v1/contexts should create a new context."""
        payload = {
            "title": "通过API创建的上下文",
            "content": "API创建的内容",
            "domain": "operations",
            "created_by": "api_test",
        }
        response = client.post("/api/v1/contexts", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == payload["title"]

    def test_create_context_missing_fields(self, client):
        """POST /api/v1/contexts with missing fields should return 400."""
        payload = {"title": "缺少content"}
        response = client.post("/api/v1/contexts", json=payload)
        assert response.status_code == 400

    def test_update_context(self, client, db):
        """PUT /api/v1/contexts/{id} should update context."""
        ctx = make_context(db, context_id="ctx_api_update", title="旧标题",
                          content="旧内容")
        payload = {"title": "新标题", "content": "新内容"}
        response = client.put(f"/api/v1/contexts/{ctx.context_id}", json=payload)
        assert response.status_code == 200

    def test_update_context_not_found(self, client):
        """PUT /api/v1/contexts/{id} should return 404 for nonexistent."""
        response = client.put("/api/v1/contexts/nonexistent", json={"title": "x"})
        assert response.status_code == 404

    def test_update_context_status(self, client, db):
        """PATCH /api/v1/contexts/{id}/status should update lifecycle status."""
        ctx = make_context(db, context_id="ctx_api_status", title="状态变更",
                          content="状态测试", lifecycle_status="active")

        response = client.patch(
            f"/api/v1/contexts/{ctx.context_id}/status",
            json={"new_status": "needs_update"},
        )
        assert response.status_code == 200

    def test_update_context_confidence(self, client, db):
        """PATCH /api/v1/contexts/{id}/confidence should update confidence."""
        ctx = make_context(db, context_id="ctx_api_conf", title="可信度变更",
                          content="可信度测试", confidence_level="L2",
                          confidence_score=0.5)

        response = client.patch(
            f"/api/v1/contexts/{ctx.context_id}/confidence",
            json={"level": "L3", "score": 0.78},
        )
        assert response.status_code == 200

    def test_update_context_confidence_not_found(self, client):
        """PATCH confidence for nonexistent should return 404."""
        response = client.patch(
            "/api/v1/contexts/nonexistent/confidence",
            json={"level": "L3"},
        )
        assert response.status_code == 404

    def test_delete_context(self, client, db):
        """DELETE /api/v1/contexts/{id} should soft-delete."""
        ctx = make_context(db, context_id="ctx_api_del", title="待删除",
                          content="删除测试")
        response = client.delete(f"/api/v1/contexts/{ctx.context_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

    def test_delete_context_not_found(self, client):
        """DELETE for nonexistent should return 404."""
        response = client.delete("/api/v1/contexts/nonexistent")
        assert response.status_code == 404

    def test_search_endpoint(self, client):
        """POST /api/v1/search should support search."""
        payload = {"query": "测试搜索"}
        response = client.post("/api/v1/search", json=payload)
        assert response.status_code == 200


class TestHealthAPI:
    """Test health check endpoints."""

    def test_root_endpoint(self, client):
        """GET / should return service info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "统一上下文管理中心"

    def test_health_endpoint(self, client):
        """GET /health should return healthy."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
