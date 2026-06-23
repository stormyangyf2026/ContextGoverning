"""Tests for MCP Server — 8 Agent tools."""
import pytest
from app.api.mcp.server import get_mcp_server, MCPServer
from app.tests.conftest import make_context, make_entity


class TestMCPServer:
    """Test all 8 MCP Tools."""

    def test_search_context(self, db):
        """search_context tool should return search results with guidance."""
        make_context(db, context_id="ctx_mcp_s01", title="MCP搜索",
                     content="MCP搜索测试内容", confidence_level="L3")

        svc = get_mcp_server()
        result = svc.search_context(db, "MCP搜索", mode="hybrid", top_k=5)

        assert "data" in result
        assert "meta" in result

    def test_get_context_detail(self, db):
        """get_context_detail should return full context with guidance."""
        ctx = make_context(db, context_id="ctx_mcp_detail", title="MCP详情",
                          content="完整详情内容", confidence_level="L4")

        svc = get_mcp_server()
        result = svc.get_context_detail(db, ctx.context_id)

        assert result["context_id"] == ctx.context_id
        assert result["title"] == "MCP详情"
        assert "consumption_guidance" in result
        assert result["consumption_guidance"]["can_agent_reference"] is True

    def test_get_context_detail_not_found(self, db):
        """get_context_detail should return error for nonexistent context."""
        svc = get_mcp_server()
        result = svc.get_context_detail(db, "nonexistent_context_id")

        assert "error" in result
        assert result["error"] == "Context not found"

    def test_get_entity_graph(self, db):
        """get_entity_graph should return entity-centric subgraph."""
        entity = make_entity(db, name="MCP实体", type="customer", domain="customer")
        ctx = make_context(db, context_id="ctx_mcp_eg", title="MCP图谱",
                          content="图谱测试")
        from app.tests.conftest import make_context_entity_map
        make_context_entity_map(db, ctx.id, entity.id)

        svc = get_mcp_server()
        result = svc.get_entity_graph(db, "MCP实体", depth=1)

        assert result["center_entity"] is not None
        assert result["center_entity"]["name"] == "MCP实体"

    def test_get_context_timeline(self, db):
        """get_context_timeline should return time-ordered contexts."""
        make_context(db, context_id="ctx_mcp_t1", title="时间线1",
                     content="时间线测试1", domain="operations")
        make_context(db, context_id="ctx_mcp_t2", title="时间线2",
                     content="时间线测试2", domain="operations")

        svc = get_mcp_server()
        result = svc.get_context_timeline(db, domain="operations", limit=10)

        assert isinstance(result, list)
        for item in result:
            assert "title" in item
            assert "created_at" in item

    def test_get_context_timeline_empty(self, db):
        """get_context_timeline should return empty list with no matching contexts."""
        svc = get_mcp_server()
        result = svc.get_context_timeline(db, domain="nonexistent_domain")

        assert result == []

    def test_get_contradictions(self, db):
        """get_contradictions should return contexts with contradicted status."""
        make_context(db, context_id="ctx_mcp_c1", title="矛盾上下文",
                     content="矛盾测试", lifecycle_status="contradicted")

        svc = get_mcp_server()
        result = svc.get_contradictions(db)

        assert "contradictions" in result
        assert "count" in result
        assert result["count"] >= 1

    def test_get_contradictions_none(self, db):
        """get_contradictions should return empty when no contradictions."""
        svc = get_mcp_server()
        result = svc.get_contradictions(db)

        assert result["count"] == 0
        assert result["contradictions"] == []

    def test_submit_context(self, db):
        """submit_context should create a new context from Agent."""
        svc = get_mcp_server()
        result = svc.submit_context(
            db,
            title="Agent提交的上下文",
            content="Agent自动提交的测试内容",
            domain="operations",
            created_by="mcp_agent",
        )

        assert result["status"] == "success"
        assert "context_id" in result

    def test_check_confidence(self, db):
        """check_confidence should return confidence level of a context."""
        ctx = make_context(db, context_id="ctx_mcp_conf", title="可信度检查",
                          content="可信度检查内容", confidence_level="L3",
                          confidence_score=0.78)

        svc = get_mcp_server()
        result = svc.check_confidence(db, ctx.context_id)

        assert result["context_id"] == ctx.context_id
        assert result["confidence_level"] == "L3"
        assert "can_reference" in result
        assert "consumption_guidance" in result

    def test_check_confidence_not_found(self, db):
        """check_confidence should return error for nonexistent context."""
        svc = get_mcp_server()
        result = svc.check_confidence(db, "nonexistent_ctx")

        assert "error" in result

    def test_submit_correction(self, db):
        """submit_correction should create correction context and mark original."""
        ctx = make_context(db, context_id="ctx_mcp_orig", title="原始上下文",
                          content="需要修正的内容", lifecycle_status="active")

        svc = get_mcp_server()
        result = svc.submit_correction(
            db,
            ctx.context_id,
            correction="这是修正后的内容",
            submitted_by="mcp_agent",
        )

        assert result["status"] == "success"
        assert result["original_context_id"] == ctx.context_id
        assert "correction_context_id" in result

    def test_submit_correction_not_found(self, db):
        """submit_correction should return error for nonexistent context."""
        svc = get_mcp_server()
        result = svc.submit_correction(
            db,
            "nonexistent_ctx",
            correction="修正内容",
        )

        assert "error" in result

    def test_eight_tools_defined(self):
        """MCPServer should have exactly 8 tool methods."""
        svc = get_mcp_server()
        tool_methods = [
            "search_context", "get_context_detail", "get_entity_graph",
            "get_context_timeline", "get_contradictions", "submit_context",
            "check_confidence", "submit_correction",
        ]
        for tool in tool_methods:
            assert hasattr(svc, tool), f"Missing tool: {tool}"

    def test_singleton_pattern(self):
        """get_mcp_server should return the same instance."""
        svc1 = get_mcp_server()
        svc2 = get_mcp_server()
        assert svc1 is svc2
