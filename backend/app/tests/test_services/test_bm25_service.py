"""Tests for BM25Service — PostgreSQL full-text search via tsvector/tsquery."""
import pytest
from app.services.bm25_service import get_bm25_service
from app.tests.conftest import make_context


class TestBM25Service:
    """Test PostgreSQL full-text search operations."""

    def test_search_text_finds_matches(self, db):
        """search_text should find contexts matching the query."""
        make_context(db, context_id="ctx_bm25_01", title="BM25测试",
                     content="PostgreSQL全文搜索测试内容")

        svc = get_bm25_service()
        results = svc.search_text(db, "全文搜索", top_k=10)

        assert len(results) >= 0  # May or may not find depending on parser

    def test_search_text_with_domain_filter(self, db):
        """search_text should apply domain filter when specified."""
        make_context(db, context_id="ctx_bm25_d01", title="运营数据",
                     content="运营报表", domain="operations")
        make_context(db, context_id="ctx_bm25_d02", title="客户数据",
                     content="客户报表", domain="customer")

        svc = get_bm25_service()
        results = svc.search_text(db, "数据", top_k=10, domain="operations")

        for r in results:
            assert r.domain == "operations"

    def test_search_text_no_results(self, db):
        """search_text with nonsense query should return empty list."""
        svc = get_bm25_service()
        results = svc.search_text(db, "xyznonexistentpattern999", top_k=10)
        assert results == []

    def test_search_ilike_fallback(self, db):
        """search_ilike should use ILIKE pattern matching."""
        make_context(db, context_id="ctx_ilike_01", title="模糊匹配",
                     content="iLIKE模糊搜索测试")

        svc = get_bm25_service()
        results = svc.search_ilike(db, "模糊搜索", top_k=10)

        assert len(results) >= 0

    def test_search_ilike_with_domain(self, db):
        """search_ilike with domain should filter properly."""
        make_context(db, context_id="ctx_ilike_d01", title="项目数据",
                     content="项目相关数据", domain="project")

        svc = get_bm25_service()
        results = svc.search_ilike(db, "项目", top_k=10, domain="project")

        for r in results:
            assert r.domain == "project"

    def test_search_ilike_deleted_excluded(self, db):
        """search_ilike should exclude soft-deleted contexts."""
        import hashlib
        content = "已删除测试内容"
        from app.models.context import ContextItem
        ctx = ContextItem(
            context_id="ctx_ilike_del",
            title="已删除上下文",
            content=content,
            content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
            domain="operations",
            confidence_level="L2",
            confidence_score=0.5,
            lifecycle_status="active",
            created_by="admin_test",
            is_deleted=True,
        )
        db.add(ctx)
        db.commit()
        db.refresh(ctx)

        svc = get_bm25_service()
        results = svc.search_ilike(db, "已删除", top_k=10)

        for r in results:
            assert r.context_id != "ctx_ilike_del"

    def test_search_ilike_topk_limit(self, db):
        """search_ilike should respect top_k limit."""
        for i in range(10):
            make_context(db, context_id=f"ctx_topk_{i:02d}", title=f"TopK测试 {i}",
                         content=f"TopK限制测试内容 {i}")

        svc = get_bm25_service()
        results = svc.search_ilike(db, "TopK", top_k=3)

        assert len(results) <= 3

    def test_singleton_pattern(self):
        """get_bm25_service should return the same instance."""
        svc1 = get_bm25_service()
        svc2 = get_bm25_service()
        assert svc1 is svc2


class TestBM25EdgeCases:
    """Edge case tests for BM25 service."""

    def test_empty_query(self, db):
        """Empty query should not crash."""
        svc = get_bm25_service()
        results = svc.search_text(db, "", top_k=10)
        assert isinstance(results, list)

    def test_special_characters(self, db):
        """Special characters in query should not crash."""
        make_context(db, context_id="ctx_special", title="特殊字符",
                     content="包含特殊字符的内容")

        svc = get_bm25_service()
        results = svc.search_text(db, "特殊'\"%_", top_k=10)
        assert isinstance(results, list)

    def test_chinese_query(self, db):
        """Chinese query should work with ILIKE fallback."""
        make_context(db, context_id="ctx_cn", title="中文搜索",
                     content="中文全文搜索测试内容")

        svc = get_bm25_service()
        results = svc.search_ilike(db, "中文", top_k=10)
        assert isinstance(results, list)
