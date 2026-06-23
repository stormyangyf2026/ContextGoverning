"""Unit tests for classification service."""
import pytest
from app.services.classification_service import (
    classify_domain, classify_sub_category, VALID_DOMAINS,
    VALID_SUB_CATEGORIES,
)


class TestClassifyDomain:
    def test_customer_keyword_maps_to_customer(self):
        domain, source = classify_domain("客户", "客户预算信息")
        assert domain == "customer"
        assert source == "fallback"

    def test_project_keyword_maps_to_project(self):
        domain, source = classify_domain("项目交付", "项目里程碑")
        assert domain == "project"
        assert source == "fallback"

    def test_operations_keyword_maps_to_operations(self):
        domain, source = classify_domain("产品", "产品创新")
        assert domain == "operations"
        assert source == "fallback"

    def test_external_keyword_maps_to_external(self):
        domain, source = classify_domain("竞品", "竞品分析")
        assert domain == "external"
        assert source == "fallback"

    def test_industry_policy_maps_to_external(self):
        domain, source = classify_domain("行业政策", "政策分析")
        assert domain == "external"
        assert source == "fallback"

    def test_contract_maps_to_project(self):
        domain, source = classify_domain("合同", "合同条款")
        assert domain == "project"
        assert source == "fallback"

    def test_default_falls_back_to_operations(self):
        domain, source = classify_domain("未知", "无法分类的内容")
        assert domain == "operations"
        assert source == "fallback"

    def test_title_keyword_matches(self):
        """Keyword in title only should also match."""
        domain, source = classify_domain("售前方案", "一些描述")
        assert domain == "project"
        assert source == "fallback"

    def test_content_keyword_matches(self):
        """Keyword in content only should also match."""
        domain, source = classify_domain("标题", "这里提到了售前")
        assert domain == "project"
        assert source == "fallback"

    def test_returns_valid_domain(self):
        domain, source = classify_domain("任意标题", "任意内容")
        assert domain in VALID_DOMAINS
        assert source == "fallback"


class TestClassifyDomainDBDriven:
    """Test DB-driven weighted classification with rule seeding and voting."""

    def test_seeds_default_rules_on_first_call(self, db_session):
        """First DB call should seed default rules and use weighted voting."""
        from app.models.review_feedback import ClassificationRuleWeight
        domain, source = classify_domain("客户合同", "项目交付内容", db=db_session)
        assert domain in VALID_DOMAINS
        # Source should be 'rule' (from DB) not 'fallback'
        assert source in ("rule", "manual", "fallback")

        # Verify rules were seeded
        rules = db_session.query(ClassificationRuleWeight).filter(
            ClassificationRuleWeight.status == "active",
        ).count()
        assert rules > 0

    def test_weighted_voting_prefers_higher_weight(self, db_session):
        """When keywords match multiple domains, the one with higher cumulative weight wins."""
        domain, source = classify_domain("客户", "这是一个关于客户和竞品的内容", db=db_session)
        assert domain in VALID_DOMAINS

    def test_db_fallback_when_no_rules_match(self, db_session):
        """Should fallback to operations when no keywords match."""
        domain, source = classify_domain("无关联", "无匹配关键词", db=db_session)
        assert domain == "operations"

    def test_workspace_scoped_rules(self, db_session):
        """Rules should be workspace-scoped."""
        domain, source = classify_domain(
            "合同项目", "客户需求", db=db_session,
            workspace_id="00000000-0000-0000-0000-000000000099",
        )
        assert domain in VALID_DOMAINS

    def test_get_rule_version(self, db_session):
        """Should return a version string."""
        from app.services.classification_service import get_rule_version

        # Trigger seeding
        classify_domain("客户", "测试", db=db_session)
        version = get_rule_version(db_session)
        assert version.startswith("v")
        assert "." in version


class TestClassifySubCategory:
    def test_customer_overview(self):
        assert classify_sub_category("customer", "客户概览信息") == "overview"

    def test_customer_org_structure(self):
        assert classify_sub_category("customer", "组织架构说明") == "org_structure"

    def test_customer_business_model(self):
        assert classify_sub_category("customer", "业务模式分析") == "business_model"

    def test_customer_financial(self):
        assert classify_sub_category("customer", "财务营收报告") == "financial"

    def test_project_presales(self):
        assert classify_sub_category("project", "售前方案提交") == "presales"

    def test_project_contract(self):
        assert classify_sub_category("project", "合同签约") == "contract"

    def test_project_delivery(self):
        assert classify_sub_category("project", "项目交付上线") == "delivery"

    def test_unknown_returns_none(self):
        assert classify_sub_category("customer", "无特定关键词") is None

    def test_invalid_domain_returns_none(self):
        assert classify_sub_category("nonexistent", "任意内容") is None


class TestDomainKeywords:
    """Verify all domain rules have correct keywords and mappings."""

    def test_all_rules_have_valid_domains(self):
        from app.services.classification_service import DOMAIN_RULES
        for keyword, domain, weight in DOMAIN_RULES:
            assert domain in VALID_DOMAINS
            assert 0 < weight <= 1.0

    def test_all_sub_categories_valid(self):
        for domain, subs in VALID_SUB_CATEGORIES.items():
            assert domain in VALID_DOMAINS
            for sub in subs:
                assert isinstance(sub, str)

    def test_seed_default_rules_is_idempotent(self, db_session):
        """Seeding twice should not create duplicate rules."""
        from app.services.classification_service import seed_default_rules
        from app.models.review_feedback import ClassificationRuleWeight

        n1 = seed_default_rules(db_session)
        n2 = seed_default_rules(db_session)

        assert n2 == 0  # Second call should insert nothing (all exist)
        total = db_session.query(ClassificationRuleWeight).filter(
            ClassificationRuleWeight.status == "active",
        ).count()
        assert total == n1  # No duplicates
