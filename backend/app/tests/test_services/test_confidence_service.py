"""Unit tests for confidence_service — the core credibility evaluation engine."""
import pytest
from datetime import date, timedelta
from app.services.confidence_service import (
    get_initial_confidence,
    resolve_level,
    level_to_median,
    can_agent_reference,
    calculate_decay,
    calculate_corroboration,
    apply_conflict_penalty,
    review_upgrade,
)


class TestInitialConfidenceMapping:
    """Test source_type → (level, score) mapping (§3.4.2)"""

    def test_contract_source_gets_l5(self):
        level, score = get_initial_confidence("contract")
        assert level == "L5"
        assert score == 0.98

    def test_official_doc_gets_l5(self):
        level, score = get_initial_confidence("official_doc")
        assert level == "L5"

    def test_expert_verified_gets_l4(self):
        level, score = get_initial_confidence("expert_verified")
        assert level == "L4"
        assert score == 0.93

    def test_financial_report_gets_l4(self):
        level, score = get_initial_confidence("financial_report")
        assert level == "L4"

    def test_meeting_minutes_gets_l4(self):
        level, score = get_initial_confidence("meeting_minutes")
        assert level == "L4"

    def test_project_kb_gets_l3(self):
        level, score = get_initial_confidence("project_kb")
        assert level == "L3"
        assert score == 0.78

    def test_memory_md_gets_l2(self):
        level, score = get_initial_confidence("memory_md")
        assert level == "L2"
        assert score == 0.65

    def test_ai_extract_gets_l2(self):
        level, score = get_initial_confidence("ai_extract")
        assert level == "L2"
        assert score == 0.60

    def test_verbal_gets_l1(self):
        level, score = get_initial_confidence("verbal")
        assert level == "L1"

    def test_competitor_rumor_gets_l1(self):
        level, score = get_initial_confidence("competitor_rumor")
        assert level == "L1"
        assert score == 0.35

    def test_lesson_learned_gets_l3(self):
        level, score = get_initial_confidence("lesson_learned")
        assert level == "L3"
        assert score == 0.78

    def test_unknown_source_defaults_to_l2(self):
        level, score = get_initial_confidence("some_unknown_type")
        assert level == "L2"
        assert score == 0.50

    def test_all_16_source_types_mapped(self):
        all_types = [
            "contract", "official_doc", "expert_verified", "financial_report",
            "meeting_minutes", "email", "project_kb", "ai_extract_verified",
            "manual_entry", "memory_md", "ai_extract", "web_scrape",
            "verbal", "unknown", "competitor_rumor", "lesson_learned",
        ]
        for st in all_types:
            level, score = get_initial_confidence(st)
            assert level in ("L0", "L1", "L2", "L3", "L4", "L5")
            assert 0.0 <= score <= 1.0


class TestLevelScoreMapping:
    """Test level ↔ score resolution (§3.4.7)"""

    def test_resolve_level_l5(self):
        assert resolve_level(0.98) == "L5"
        assert resolve_level(0.95) == "L5"

    def test_resolve_level_l4(self):
        assert resolve_level(0.94) == "L4"
        assert resolve_level(0.85) == "L4"

    def test_resolve_level_l3(self):
        assert resolve_level(0.84) == "L3"
        assert resolve_level(0.70) == "L3"

    def test_resolve_level_l2(self):
        assert resolve_level(0.69) == "L2"
        assert resolve_level(0.50) == "L2"

    def test_resolve_level_l1(self):
        assert resolve_level(0.49) == "L1"
        assert resolve_level(0.30) == "L1"

    def test_resolve_level_l0(self):
        assert resolve_level(0.29) == "L0"
        assert resolve_level(0.0) == "L0"

    def test_level_to_median_l5(self):
        assert level_to_median("L5") == 0.975

    def test_level_to_median_l3(self):
        assert level_to_median("L3") == 0.775

    def test_level_to_median_l1(self):
        assert level_to_median("L1") == 0.40

    def test_level_to_median_unknown(self):
        assert level_to_median("INVALID") == 0.5


class TestAgentReferenceDecision:
    """Test Agent reference decision table (§3.4.8)"""

    def test_l5_can_reference_freely(self):
        can_ref, msg = can_agent_reference("L5")
        assert can_ref is True
        assert "自由引用" in msg

    def test_l4_can_reference_with_source(self):
        can_ref, msg = can_agent_reference("L4")
        assert can_ref is True
        assert "来源" in msg

    def test_l3_can_reference_with_caution(self):
        can_ref, msg = can_agent_reference("L3")
        assert can_ref is True
        assert "人工复核" in msg

    def test_l2_cannot_reference(self):
        can_ref, msg = can_agent_reference("L2")
        assert can_ref is False

    def test_l1_cannot_reference(self):
        can_ref, msg = can_agent_reference("L1")
        assert can_ref is False

    def test_l0_cannot_reference(self):
        can_ref, msg = can_agent_reference("L0")
        assert can_ref is False

    def test_unknown_level_cannot_reference(self):
        can_ref, msg = can_agent_reference("INVALID")
        assert can_ref is False


class TestTimeBasedDecay:
    """Test time-based confidence decay (§3.4.4)"""

    def test_no_decay_within_grace_period(self):
        """Recently updated content should not decay."""
        today = date.today()
        recent = today - timedelta(days=30)  # 1 month ago
        effective, level = calculate_decay(0.80, recent)
        assert effective == 0.80

    def test_decay_after_grace_period(self):
        """Content older than 6 months should decay."""
        today = date.today()
        old = today - timedelta(days=365)  # 12 months ago
        effective, level = calculate_decay(0.80, old)
        assert effective < 0.80

    def test_decay_does_not_drop_below_min(self):
        """Decay should not drop score below configured minimum."""
        today = date.today()
        ancient = today - timedelta(days=365 * 5)  # 5 years ago
        effective, _ = calculate_decay(0.50, ancient)
        assert effective >= 0.20  # MIN_SCORE_AFTER_DECAY

    def test_decay_preserves_level_consistency(self):
        """Decayed score should map to correct level."""
        today = date.today()
        old = today - timedelta(days=500)
        effective, level = calculate_decay(0.75, old)
        assert resolve_level(effective) == level


class TestMultiSourceCorroboration:
    """Test multi-source corroboration boost (§3.4.3)"""

    def test_boost_increases_score(self):
        new_score, count = calculate_corroboration(0.65, 0.90)
        assert new_score > 0.65
        assert count == 1

    def test_diminishing_returns_after_3_sources(self):
        # After 3 corroborations, boost is halved
        new_score, count = calculate_corroboration(0.80, 0.85, existing_corroboration_count=3)
        assert new_score > 0.80
        assert count == 4

    def test_score_capped_at_one(self):
        new_score, _ = calculate_corroboration(0.98, 0.99)
        assert new_score <= 1.0

    def test_boost_capped_by_max_corroboration(self):
        new_score, _ = calculate_corroboration(0.50, 0.90)
        # Max boost is 0.45, so score <= 0.95
        assert new_score <= 0.95


class TestContradictionPenalty:
    """Test contradiction penalty (§3.4.5)"""

    def test_penalty_reduces_score(self):
        result = apply_conflict_penalty(0.75)
        assert result < 0.75

    def test_penalty_has_floor(self):
        result = apply_conflict_penalty(0.15)
        assert result >= 0.10


class TestReviewUpgrade:
    """Test L2→L3 review upgrade (§3.4.6)"""

    def test_review_upgrade_returns_l3(self):
        level, score = review_upgrade()
        assert level in ("L3",)
        assert score >= 0.75
