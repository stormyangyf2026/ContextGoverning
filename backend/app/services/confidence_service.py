"""Confidence engine — the core component for evaluating and managing context credibility.

Implements four sub-algorithms:
    1. Initial confidence mapping (source_type → level/score)
    2. Multi-source corroboration boost
    3. Time-based decay
    4. Contradiction penalty
    5. Manual review override

All tunable parameters are read from Settings (env vars / .env file);
code-level constants are used as fallback defaults only.
"""
from datetime import date
from typing import Optional, Tuple
from app.config import get_settings

_settings = get_settings()

# ---- Initial Confidence Mapping (Design Doc §3.4.2) ----
# These are the default source-type → (level, score) mappings.
# They can be overridden at runtime via the config_service (DB > env > YAML),
# but the code-level defaults serve as the fallback.

INITIAL_CONFIDENCE_MAP: dict[str, Tuple[str, float]] = {
    "contract":             ("L5", 0.98),
    "official_doc":         ("L5", 0.97),
    "expert_verified":      ("L4", 0.93),
    "financial_report":     ("L4", 0.92),
    "meeting_minutes":      ("L4", 0.90),
    "email":                ("L4", 0.88),
    "project_kb":           ("L3", 0.78),
    "ai_extract_verified":  ("L3", 0.78),
    "manual_entry":         ("L3", 0.75),
    "memory_md":            ("L2", 0.65),
    "ai_extract":           ("L2", 0.60),
    "web_scrape":           ("L2", 0.55),
    "verbal":               ("L1", 0.40),
    "unknown":              ("L1", 0.40),
    "competitor_rumor":     ("L1", 0.35),
    "lesson_learned":       ("L3", 0.78),
}


def get_initial_confidence(source_type: str) -> Tuple[str, float]:
    """Get initial confidence level and score for a source type."""
    level, score = INITIAL_CONFIDENCE_MAP.get(source_type, ("L2", 0.50))
    return level, score


# ---- Level ↔ Score Mapping (Design Doc §3.4.7) ----
# Level thresholds are stable business logic; not expected to change often.

def resolve_level(score: float) -> str:
    """Convert a confidence score to its level."""
    if score >= 0.95:
        return "L5"
    if score >= 0.85:
        return "L4"
    if score >= 0.70:
        return "L3"
    if score >= 0.50:
        return "L2"
    if score >= 0.30:
        return "L1"
    return "L0"


def level_to_median(level: str) -> float:
    """Get the median score for a confidence level."""
    return {
        "L5": 0.975, "L4": 0.90, "L3": 0.775,
        "L2": 0.60, "L1": 0.40, "L0": 0.15,
    }.get(level, 0.5)


# ---- Agent Reference Decision Table (§3.4.8) ----

def can_agent_reference(level: str) -> Tuple[bool, str]:
    """Determine if an Agent can reference a context at this confidence level."""
    rules = {
        "L5": (True, "自由引用，建议保留原始出处链接"),
        "L4": (True, "引用时请标注来源"),
        "L3": (True, "引用时请提示此信息来源于AI提取，建议人工复核"),
        "L2": (False, "此信息尚未经人工审核，不可直接引用"),
        "L1": (False, "信息可信度较低，仅作参考"),
        "L0": (False, "信息已过期或存在矛盾，不可引用"),
    }
    return rules.get(level, (False, "未知可信度等级"))


# ---- Time-based Decay (§3.4.4) ----
# Parameters loaded from Settings (env vars / .env file).

def _decay_start_months() -> float:
    return _settings.confidence_decay_start_months

def _decay_rate_per_month() -> float:
    return _settings.confidence_decay_rate_per_month

def _min_score_after_decay() -> float:
    return _settings.confidence_decay_min_score

def _conflict_penalty() -> float:
    return _settings.confidence_conflict_penalty

def _max_corroboration_boost() -> float:
    return _settings.confidence_corroboration_max_boost

def _review_upgrade_level() -> str:
    return _settings.confidence_review_upgrade_level

def _review_upgrade_score() -> float:
    return _settings.confidence_review_upgrade_score


def calculate_decay(original_score: float, last_updated: date) -> Tuple[float, str]:
    """Calculate time-decayed confidence score.

    Returns (effective_score, new_level).
    """
    today = date.today()
    months_since = (today - last_updated).days / 30.0

    if months_since <= _decay_start_months():
        return original_score, resolve_level(original_score)

    decay = _decay_rate_per_month() * (months_since - _decay_start_months())
    effective = max(original_score - decay, _min_score_after_decay())
    return effective, resolve_level(effective)


# ---- Multi-source Corroboration (§3.4.3) ----


def calculate_corroboration(
    existing_score: float,
    new_source_score: float,
    existing_corroboration_count: int = 0,
) -> Tuple[float, int]:
    """Calculate corroboration boost when a new source confirms existing context.

    Returns (new_score, new_corroboration_count).
    """
    weight = min(0.15, max(0, (new_source_score - 0.5) * 0.3))
    boost = (1.0 - existing_score) * weight

    # Diminishing returns: same-type sources after 3
    if existing_corroboration_count >= 3:
        boost *= 0.5

    # Cap total boost
    max_boost = _max_corroboration_boost()
    new_score = min(existing_score + boost, existing_score + max_boost)
    new_score = min(new_score, 1.0)

    return new_score, existing_corroboration_count + 1


# ---- Contradiction Penalty (§3.4.5) ----

def apply_conflict_penalty(current_score: float) -> float:
    """Penalize both sides of a contradiction."""
    return max(current_score - _conflict_penalty(), 0.10)


# ---- L2→L3 Review Upgrade (§3.4.6) ----

def review_upgrade() -> Tuple[str, float]:
    """Standard upgrade when context passes AI extraction review."""
    return _review_upgrade_level(), _review_upgrade_score()
