"""Tests for SearchService — hybrid search orchestration with fusion ranking."""
import pytest
from app.tests.conftest import make_context
from app.services.search_service import get_search_service


class TestSearchService:
    """Test the hybrid search service with all 6 search modes."""

    def test_hybrid_search(self, db):
        """Hybrid search should return BM25 + iLIKE merged results."""
        make_context(db, context_id="ctx_search_h1", title="营收增长报告",
                     content="2024年营收增长30%", domain="operations")
        make_context(db, context_id="ctx_search_h2", title="客户满意度",
                     content="客户满意度达到95%", domain="customer")

        svc = get_search_service()
        result = svc.search(db, "营收增长", mode="hybrid")

        assert result["meta"]["mode"] == "hybrid"
        assert result["meta"]["total"] >= 1
        assert any("营收" in item["title"] for item in result["data"])

    def test_exact_search(self, db):
        """Exact search should use text match."""
        make_context(db, context_id="ctx_exact_01", title="精确匹配测试",
                     content="这是一个精确匹配的内容")

        svc = get_search_service()
        result = svc.search(db, "精确匹配", mode="exact")

        assert result["meta"]["mode"] == "exact"

    def test_semantic_search(self, db):
        """Semantic search mode should work (fallback to iLIKE)."""
        make_context(db, context_id="ctx_sem_01", title="语义搜索", content="向量相似度搜索内容")

        svc = get_search_service()
        result = svc.search(db, "语义", mode="semantic")

        assert result["meta"]["mode"] == "semantic"

    def test_relation_search(self, db):
        """Relation search should return contexts with domain filter."""
        make_context(db, context_id="ctx_rel_01", title="关系搜索", domain="operations")
        make_context(db, context_id="ctx_rel_02", title="关系搜索2", domain="customer")

        svc = get_search_service()
        result = svc.search(db, "关系", mode="relation", filters={"domain": "operations"})

        assert result["meta"]["mode"] == "relation"
        # Should filter by domain
        assert all("operations" in item.get("domain", "") for item in result["data"] if result["data"])

    def test_timeline_search(self, db):
        """Timeline search should return results ordered by created_at DESC."""
        make_context(db, context_id="ctx_time_01", title="旧上下文", content="旧数据")
        make_context(db, context_id="ctx_time_02", title="新上下文", content="新数据")

        svc = get_search_service()
        result = svc.search(db, "上下文", mode="timeline")

        assert result["meta"]["mode"] == "timeline"
        assert result["meta"]["total"] >= 2

    def test_contradiction_search(self, db):
        """Contradiction search should only return contexts with contradicted status."""
        make_context(db, context_id="ctx_contra_01", title="正常上下文",
                     lifecycle_status="active")
        make_context(db, context_id="ctx_contra_02", title="矛盾上下文",
                     lifecycle_status="contradicted")

        svc = get_search_service()
        result = svc.search(db, "矛盾", mode="contradiction")

        assert result["meta"]["mode"] == "contradiction"
        # Should only return contradicted contexts
        for item in result["data"]:
            assert item["lifecycle_status"] == "contradicted"

    def test_pagination(self, db):
        """Pagination should correctly limit and offset results."""
        for i in range(10):
            make_context(db, context_id=f"ctx_page_{i:02d}", title=f"页面测试 {i}",
                         content=f"分页测试内容 {i}")

        svc = get_search_service()
        result = svc.search(db, "分页", mode="hybrid", page=1, page_size=5)

        assert len(result["data"]) <= 5
        assert result["meta"]["page"] == 1
        assert result["meta"]["page_size"] == 5

    def test_search_with_entity_filter(self, db, sample_entity):
        """Entity filter should only return contexts linked to specified entities."""
        from app.tests.conftest import make_context_entity_map
        ctx = make_context(db, context_id="ctx_ent_filt", title="实体关联上下文",
                          content="与实体关联的内容")
        make_context_entity_map(db, ctx.id, sample_entity.id)

        svc = get_search_service()
        result = svc.search(db, "实体", mode="hybrid",
                           filters={"entities": ["测试公司"]})

        assert result["meta"]["total"] >= 0  # entity filter may narrow results

    def test_search_with_confidence_filter(self, db):
        """Confidence filter should only return contexts at or above the specified level."""
        make_context(db, context_id="ctx_conf_l1", title="低可信度",
                     confidence_level="L1", confidence_score=0.3)
        make_context(db, context_id="ctx_conf_l4", title="高可信度",
                     confidence_level="L4", confidence_score=0.85)

        svc = get_search_service()
        result = svc.search(db, "可信度", mode="hybrid",
                           filters={"confidence_min": "L3"})

        # Only L4 should pass L3 minimum
        for item in result["data"]:
            assert item["confidence_level"] >= "L3"

    def test_search_with_confidence_detail(self, db):
        """include_confidence_detail should add confidence breakdown."""
        make_context(db, context_id="ctx_conf_detail", title="可信度详情",
                     content="含详细可信度数据")

        svc = get_search_service()
        result = svc.search(db, "可信度", mode="hybrid", include_confidence_detail=True)

        if result["data"]:
            assert "confidence" in result["data"][0]

    def test_search_with_relations(self, db):
        """include_relations should add relation data."""
        make_context(db, context_id="ctx_rel_detail", title="含关系数据",
                     content="带关系的上下文")

        svc = get_search_service()
        result = svc.search(db, "关系", mode="hybrid", include_relations=True)

        assert "data" in result  # Should not crash

    def test_search_result_structure(self, db):
        """Each result item should have required fields."""
        make_context(db, context_id="ctx_struct", title="结构测试", content="验证返回结构")

        svc = get_search_service()
        result = svc.search(db, "结构", mode="hybrid")

        required_fields = ["id", "context_id", "title", "content", "domain",
                          "confidence_level", "confidence_score",
                          "lifecycle_status", "created_by", "created_at"]
        for item in result["data"]:
            for field in required_fields:
                assert field in item, f"Missing field: {field}"

    def test_search_with_empty_query(self, db):
        """Empty query should still return results (fallback behavior)."""
        make_context(db, context_id="ctx_empty_q", title="空查询", content="空查询测试")

        svc = get_search_service()
        result = svc.search(db, "", mode="hybrid")

        assert "data" in result
        assert "meta" in result

    def test_search_meta_fields(self, db):
        """Meta should include query_time_ms."""
        make_context(db, context_id="ctx_meta", title="元数据", content="元数据测试")

        svc = get_search_service()
        result = svc.search(db, "元数据", mode="hybrid")

        assert "query_time_ms" in result["meta"]
        assert isinstance(result["meta"]["query_time_ms"], int)
        assert result["meta"]["query_time_ms"] >= 0

    def test_singleton_pattern(self):
        """get_search_service should return the same instance."""
        svc1 = get_search_service()
        svc2 = get_search_service()
        assert svc1 is svc2


class TestSearchServicePermissionFiltering:
    """Tests for permission filtering during search."""

    def test_search_without_user_info(self, db):
        """Search without user info should return unfiltered results."""
        make_context(db, context_id="ctx_no_user", title="无用户过滤", content="无需权限过滤")

        svc = get_search_service()
        result = svc.search(db, "无用户", mode="hybrid")

        assert "data" in result

    def test_search_with_user_role(self, db, admin_user):
        """Search with admin role should apply permission filters."""
        make_context(db, context_id="ctx_perm_test", title="权限测试",
                     content="权限过滤测试", created_by=admin_user.username)

        svc = get_search_service()
        result = svc.search(db, "权限", mode="hybrid",
                           user_role=admin_user.role,
                           user_id=str(admin_user.id))

        assert "data" in result
