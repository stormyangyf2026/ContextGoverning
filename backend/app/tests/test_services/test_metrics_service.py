"""Tests for MetricsService — KPI collection and analysis."""
import pytest
from app.services.metrics_service import get_metrics_service
from app.tests.conftest import make_context


class TestMetricsService:
    """Test KPI metrics collection and analysis."""

    def test_get_overview(self, db):
        """get_overview should return total counts and confidence distribution."""
        make_context(db, context_id="ctx_met_01", title="指标1",
                     content="指标测试1", domain="operations",
                     confidence_level="L2", lifecycle_status="active")
        make_context(db, context_id="ctx_met_02", title="指标2",
                     content="指标测试2", domain="customer",
                     confidence_level="L4", lifecycle_status="active")

        svc = get_metrics_service()
        result = svc.get_overview(db)

        assert "total_contexts" in result
        assert result["total_contexts"] >= 2
        assert "total_entities" in result
        assert "total_relations" in result
        assert "confidence_distribution" in result

    def test_get_coverage(self, db):
        """get_coverage should return domain coverage metrics."""
        make_context(db, context_id="ctx_cov_01", title="覆盖测试1",
                     content="覆盖1", domain="operations")
        make_context(db, context_id="ctx_cov_02", title="覆盖测试2",
                     content="覆盖2", domain="customer")

        svc = get_metrics_service()
        result = svc.get_coverage(db)

        assert "domain_coverage" in result
        assert "operations" in result["domain_coverage"]
        assert "customer" in result["domain_coverage"]

    def test_get_freshness(self, db):
        """get_freshness should return time-based freshness metrics."""
        make_context(db, context_id="ctx_fresh_01", title="新鲜度1",
                     content="新鲜度测试1")

        svc = get_metrics_service()
        result = svc.get_freshness(db)

        assert "recent_contexts" in result
        assert "total_contexts" in result
        assert "freshness_ratio" in result
        assert "lifecycle_status" in result

    def test_get_confidence_trends(self, db):
        """get_confidence_trends should return confidence trends list."""
        make_context(db, context_id="ctx_trend_01", title="趋势1",
                     content="趋势1", confidence_level="L2",
                     confidence_score=0.5)
        make_context(db, context_id="ctx_trend_02", title="趋势2",
                     content="趋势2", confidence_level="L4",
                     confidence_score=0.85)

        svc = get_metrics_service()
        result = svc.get_confidence_trends(db)

        assert isinstance(result, list)
        assert len(result) >= 2
        for item in result:
            assert "confidence_score" in item
            assert "confidence_level" in item

    def test_overview_with_no_data(self, db):
        """get_overview should work with no contexts."""
        svc = get_metrics_service()
        result = svc.get_overview(db)

        assert result["total_contexts"] == 0
        assert isinstance(result["confidence_distribution"], dict)

    def test_coverage_with_no_data(self, db):
        """get_coverage should work with no contexts."""
        svc = get_metrics_service()
        result = svc.get_coverage(db)

        assert "domain_coverage" in result
        assert result["domain_coverage"] == {}

    def test_freshness_with_no_data(self, db):
        """get_freshness should work with no contexts."""
        svc = get_metrics_service()
        result = svc.get_freshness(db)

        assert result["total_contexts"] == 0

    def test_singleton_pattern(self):
        """get_metrics_service should return the same instance."""
        svc1 = get_metrics_service()
        svc2 = get_metrics_service()
        assert svc1 is svc2
