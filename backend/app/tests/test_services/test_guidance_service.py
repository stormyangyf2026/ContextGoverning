"""Tests for GuidanceService — Agent consumption guidance generation."""
import pytest
from app.services.guidance_service import get_guidance_service
from app.tests.conftest import make_context


class TestGuidanceService:
    """Test Agent consumption guidance generation for all confidence levels."""

    def test_generate_guidance_l0(self, db):
        """L0 context should NOT be referenceable."""
        ctx = make_context(db, context_id="ctx_guide_l0", title="L0上下文",
                          content="L0级内容", confidence_level="L0",
                          confidence_score=0.1, confidence_source_type="manual_entry")

        svc = get_guidance_service()
        result = svc.generate_guidance(ctx)

        assert result["can_agent_reference"] is False
        assert "context_id" in result
        assert "usage_advice" in result

    def test_generate_guidance_l1(self, db):
        """L1 context should NOT be referenceable."""
        ctx = make_context(db, context_id="ctx_guide_l1", title="L1上下文",
                          content="L1级内容", confidence_level="L1",
                          confidence_score=0.25)

        svc = get_guidance_service()
        result = svc.generate_guidance(ctx)

        assert result["can_agent_reference"] is False

    def test_generate_guidance_l2(self, db):
        """L2 context should be referenceable with caution."""
        ctx = make_context(db, context_id="ctx_guide_l2", title="L2上下文",
                          content="L2级内容", confidence_level="L2",
                          confidence_score=0.5)

        svc = get_guidance_service()
        result = svc.generate_guidance(ctx)

        assert result["can_agent_reference"] is True
        assert "reference_hint" in result

    def test_generate_guidance_l3(self, db):
        """L3 context should be referenceable as multi-source corroborated."""
        ctx = make_context(db, context_id="ctx_guide_l3", title="L3上下文",
                          content="L3级内容", confidence_level="L3",
                          confidence_score=0.78)

        svc = get_guidance_service()
        result = svc.generate_guidance(ctx)

        assert result["can_agent_reference"] is True

    def test_generate_guidance_l4(self, db):
        """L4 context should be referenceable as expert-reviewed."""
        ctx = make_context(db, context_id="ctx_guide_l4", title="L4上下文",
                          content="L4级内容", confidence_level="L4",
                          confidence_score=0.88)

        svc = get_guidance_service()
        result = svc.generate_guidance(ctx)

        assert result["can_agent_reference"] is True

    def test_generate_guidance_l5(self, db):
        """L5 context should be fully trusted."""
        ctx = make_context(db, context_id="ctx_guide_l5", title="L5上下文",
                          content="L5级内容", confidence_level="L5",
                          confidence_score=0.95)

        svc = get_guidance_service()
        result = svc.generate_guidance(ctx)

        assert result["can_agent_reference"] is True

    def test_cross_validation_for_low_confidence(self, db):
        """Low confidence contexts should have cross-validation suggestions."""
        ctx = make_context(db, context_id="ctx_cv_low", title="低可信度",
                          content="需要交叉验证", confidence_level="L1",
                          confidence_score=0.2)

        svc = get_guidance_service()
        result = svc.generate_guidance(ctx)

        assert result["cross_validation_suggestion"] is not None
        assert "交叉验证" in result["cross_validation_suggestion"]

    def test_cross_validation_for_high_confidence(self, db):
        """High confidence contexts should NOT have cross-validation suggestions."""
        ctx = make_context(db, context_id="ctx_cv_high", title="高可信度",
                          content="不需要交叉验证", confidence_level="L4",
                          confidence_score=0.88)

        svc = get_guidance_service()
        result = svc.generate_guidance(ctx)

        assert result["cross_validation_suggestion"] is None

    def test_lifecycle_warning_decaying(self, db):
        """Decaying contexts should have lifecycle warning."""
        ctx = make_context(db, context_id="ctx_lw_decay", title="衰减中",
                          content="衰减测试", lifecycle_status="decaying")

        svc = get_guidance_service()
        result = svc.generate_guidance(ctx)

        assert result["lifecycle_warning"] is not None
        assert "衰减" in result["lifecycle_warning"]

    def test_lifecycle_warning_contradicted(self, db):
        """Contradicted contexts should have lifecycle warning."""
        ctx = make_context(db, context_id="ctx_lw_contra", title="矛盾中",
                          content="矛盾测试", lifecycle_status="contradicted")

        svc = get_guidance_service()
        result = svc.generate_guidance(ctx)

        assert result["lifecycle_warning"] is not None
        assert "矛盾" in result["lifecycle_warning"]

    def test_lifecycle_warning_active(self, db):
        """Active contexts should NOT have lifecycle warning."""
        ctx = make_context(db, context_id="ctx_lw_active", title="活跃",
                          content="活跃测试", lifecycle_status="active")

        svc = get_guidance_service()
        result = svc.generate_guidance(ctx)

        assert result["lifecycle_warning"] is None

    def test_experience_marks_lesson_learned(self, db):
        """Lesson learned contexts should have experience marks."""
        ctx = make_context(db, context_id="ctx_exp_ll", title="经验教训",
                          content="经验教训内容",
                          confidence_source_type="lesson_learned")

        svc = get_guidance_service()
        result = svc.generate_guidance(ctx)

        assert result["experience_marks"] is not None
        assert result["experience_marks"]["is_lesson_learned"] is True

    def test_experience_marks_regular(self, db):
        """Regular contexts should NOT have experience marks."""
        ctx = make_context(db, context_id="ctx_exp_reg", title="常规",
                          content="常规内容",
                          confidence_source_type="manual_entry")

        svc = get_guidance_service()
        result = svc.generate_guidance(ctx)

        assert result["experience_marks"] is None

    def test_guidance_structure(self, db):
        """Guidance should have all required fields."""
        ctx = make_context(db, context_id="ctx_guide_struct", title="结构",
                          content="结构检查")

        svc = get_guidance_service()
        result = svc.generate_guidance(ctx)

        required = ["context_id", "can_agent_reference", "usage_advice",
                   "reference_hint", "cross_validation_suggestion",
                   "lifecycle_warning", "experience_marks"]
        for field in required:
            assert field in result, f"Missing field: {field}"

    def test_unknown_confidence_level(self, db):
        """Unknown confidence level should default to not referenceable."""
        ctx = make_context(db, context_id="ctx_unknown", title="未知等级",
                          content="未知等级", confidence_level="XX",
                          confidence_score=0.5)

        svc = get_guidance_service()
        result = svc.generate_guidance(ctx)

        assert result["can_agent_reference"] is False

    def test_batch_generate(self, db):
        """batch_generate should generate guidance for multiple contexts."""
        ctx1 = make_context(db, context_id="ctx_batch_1", title="批量1",
                           content="批量测试1", confidence_level="L2")
        ctx2 = make_context(db, context_id="ctx_batch_2", title="批量2",
                           content="批量测试2", confidence_level="L4")

        svc = get_guidance_service()
        result = svc.batch_generate(db, [ctx1, ctx2])

        assert result["count"] == 2
        assert len(result["guidance"]) == 2
        assert result["guidance"][0]["can_agent_reference"] is True
        assert result["guidance"][1]["can_agent_reference"] is True

    def test_singleton_pattern(self):
        """get_guidance_service should return the same instance."""
        svc1 = get_guidance_service()
        svc2 = get_guidance_service()
        assert svc1 is svc2
