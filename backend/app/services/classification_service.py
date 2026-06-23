"""Classification service — auto-classifies contexts into the four domains.

Supports two modes:
1. **Fallback mode** (no DB session): Uses hardcoded DOMAIN_RULES with first-match logic.
   This ensures backward compatibility with existing tests and basic operation.
2. **DB-driven mode** (with DB session): Loads weighted rules from classification_rule_weights
   table. Uses weighted voting — each matched keyword contributes its weight to the target
   domain, and the domain with the highest cumulative weight wins.

The DB mode also seeds default rules on first access and records classification_source
on the context item for tracking (rule / learned / manual).
"""

from typing import Optional, Dict, List, Tuple
from collections import defaultdict

VALID_DOMAINS = ("customer", "project", "operations", "external")
VALID_SUB_CATEGORIES = {
    "customer": ["overview", "org_structure", "business_model", "financial"],
    "project": ["presales", "contract", "delivery", "finance"],
    "operations": ["product_innovation", "capability", "business_mgmt", "knowledge"],
    "external": ["industry_policy", "competitor", "tech_trend", "ecosystem"],
}

# Rule-based classification: keyword → (domain, default_weight)
# These serve as both the fallback rules AND the seed data for DB initialization.
DOMAIN_RULES: List[Tuple[str, str, float]] = [
    ("客户", "customer", 0.90),
    ("客户预算", "customer", 0.85),
    ("营收", "customer", 0.80),
    ("组织架构", "customer", 0.85),
    ("项目", "project", 0.90),
    ("交付", "project", 0.85),
    ("里程碑", "project", 0.80),
    ("售前", "project", 0.85),
    ("合同", "project", 0.90),
    ("产品", "operations", 0.85),
    ("能力建设", "operations", 0.80),
    ("知识资产", "operations", 0.75),
    ("行业", "external", 0.85),
    ("竞品", "external", 0.90),
    ("政策", "external", 0.85),
    ("技术趋势", "external", 0.80),
]

# Sub-category keyword mapping — kept as hardcoded since sub-categories are finer-grained
# and less likely to benefit from rule learning in the initial phases.
SUB_CATEGORY_KEYWORDS = {
    "overview": ["概览", "概述", "概况"],
    "org_structure": ["组织架构", "部门", "团队"],
    "business_model": ["业务模式", "商业模式"],
    "financial": ["财务", "财报", "营收", "利润"],
    "presales": ["售前", "方案", "投标"],
    "contract": ["合同", "签约", "条款"],
    "delivery": ["交付", "上线", "实施"],
    "product_innovation": ["产品创新", "新产品"],
    "capability": ["能力建设", "培训", "技能"],
    "business_mgmt": ["业务管理", "流程"],
    "knowledge": ["知识", "文档", "经验"],
    "industry_policy": ["政策", "法规", "监管"],
    "competitor": ["竞品", "竞争对手"],
    "tech_trend": ["技术趋势", "技术栈"],
    "ecosystem": ["生态", "合作伙伴"],
}

# Flag to avoid seeding multiple times in the same process
_seeded_defaults = False


# ── Public API ────────────────────────────────────────────────────

def classify_domain(
    title: str,
    content: str,
    db: Optional[object] = None,
    workspace_id: Optional[str] = None,
) -> Tuple[str, str]:
    """Classify a context into a domain.

    Args:
        title: Context title text.
        content: Context content text.
        db: Optional SQLAlchemy Session. When provided, uses DB-driven weighted
            rules with weighted voting. When None, uses first-match fallback.
        workspace_id: Optional workspace ID for rule scoping.

    Returns:
        Tuple of (domain, classification_source) where source is one of:
        'rule' (fallback), 'learned', 'manual'
    """
    combined = f"{title} {content}"

    if db is not None:
        return _classify_weighted(combined, db, workspace_id)
    else:
        return _classify_fallback(combined)


def classify_sub_category(domain: str, content: str) -> Optional[str]:
    """Suggest a sub-category within a domain.

    Sub-category classification uses hardcoded keyword matching since
    sub-categories are finer-grained and tied to domain structure.
    """
    candidates = VALID_SUB_CATEGORIES.get(domain, [])
    for cat in candidates:
        for kw in SUB_CATEGORY_KEYWORDS.get(cat, []):
            if kw in content:
                return cat
    return None


# ── DB-driven Weighted Classification ────────────────────────────

def _classify_weighted(
    combined: str, db: object, workspace_id: Optional[str] = None,
) -> Tuple[str, str]:
    """Weighted voting classification using rules from DB.

    Each keyword found in the text contributes its weight to the target domain.
    The domain with the highest cumulative weight wins.
    Rules with status='deprecated' are excluded.
    Falls back to hardcoded rules if no DB rules match.
    """
    _seed_default_rules_if_needed(db, workspace_id)

    rules = _load_active_rules(db, workspace_id)

    if not rules:
        return _classify_fallback(combined)

    # Weighted voting: accumulate weight per domain for each matched keyword
    domain_scores: Dict[str, float] = defaultdict(float)
    matched_sources: Dict[str, str] = {}

    for keyword, domain, weight, source in rules:
        if keyword in combined:
            domain_scores[domain] += weight
            # Track the most "learned" source; prefer learned > manual > rule
            current = matched_sources.get(domain, "rule")
            if source == "learned" or (source == "manual" and current == "rule"):
                matched_sources[domain] = source

    if domain_scores:
        best_domain = max(domain_scores, key=domain_scores.get)
        best_source = matched_sources.get(best_domain, "rule")
        return (best_domain, best_source)

    return _classify_fallback(combined)


def _load_active_rules(
    db: object, workspace_id: Optional[str] = None,
) -> List[Tuple[str, str, float, str]]:
    """Load active weighted rules from the database.

    Returns list of (keyword, domain, weight, source) tuples sorted by weight desc.
    """
    try:
        from app.models.review_feedback import ClassificationRuleWeight

        query = db.query(ClassificationRuleWeight).filter(
            ClassificationRuleWeight.status == "active",
            ClassificationRuleWeight.weight > 0,
        )
        if workspace_id:
            query = query.filter(
                ClassificationRuleWeight.workspace_id == workspace_id,
            )

        rules = query.order_by(ClassificationRuleWeight.weight.desc()).all()
        return [
            (r.rule_keyword, r.target_domain, r.weight or 0.5, r.source or "manual")
            for r in rules
        ]
    except Exception:
        # Gracefully fall back on any DB error (e.g. table doesn't exist yet)
        return []


# ── Fallback Classification ───────────────────────────────────────

def _classify_fallback(combined: str) -> Tuple[str, str]:
    """First-match classification using hardcoded DOMAIN_RULES.

    Used when no DB session is available or no DB rules match.
    Returns (domain, 'fallback').
    """
    for keyword, domain, _weight in DOMAIN_RULES:
        if keyword in combined:
            return (domain, "fallback")
    return ("operations", "fallback")


# ── DB Rule Seeding ───────────────────────────────────────────────

def seed_default_rules(db: object, workspace_id: Optional[str] = None) -> int:
    """Seed the classification_rule_weights table with default rules.

    Only inserts rules that don't already exist for the given workspace.
    Returns the number of rules inserted.
    """
    try:
        from app.models.review_feedback import ClassificationRuleWeight
    except ImportError:
        return 0

    existing = set()
    query = db.query(ClassificationRuleWeight)
    if workspace_id:
        query = query.filter(ClassificationRuleWeight.workspace_id == workspace_id)
    for rule in query.all():
        existing.add((rule.rule_keyword, rule.target_domain))

    inserted = 0
    for keyword, domain, weight in DOMAIN_RULES:
        if (keyword, domain) not in existing:
            rule = ClassificationRuleWeight(
                rule_keyword=keyword,
                target_domain=domain,
                weight=weight,
                status="active",
                source="manual",
            )
            if workspace_id:
                rule.workspace_id = workspace_id
            db.add(rule)
            inserted += 1

    if inserted:
        db.commit()
    return inserted


def _seed_default_rules_if_needed(
    db: object, workspace_id: Optional[str] = None,
) -> None:
    """Seed default rules on first DB-driven classification call."""
    global _seeded_defaults
    if not _seeded_defaults:
        seed_default_rules(db, workspace_id)
        _seeded_defaults = True


def get_rule_version(db: object, workspace_id: Optional[str] = None) -> str:
    """Get a version string for the current rule set.

    Used for tracking which rules were active when a context was classified.
    Format: "v{count}.{hash}" where hash is derived from rule IDs.
    """
    try:
        from app.models.review_feedback import ClassificationRuleWeight

        query = db.query(ClassificationRuleWeight).filter(
            ClassificationRuleWeight.status == "active",
        )
        if workspace_id:
            query = query.filter(ClassificationRuleWeight.workspace_id == workspace_id)

        rules = query.order_by(ClassificationRuleWeight.id).all()
        if not rules:
            return "v0.fallback"

        count = len(rules)
        # Simple hash from last rule's updated_at timestamp
        latest = max(
            (r.updated_at for r in rules if r.updated_at),
            default=None,
        )
        hash_suffix = latest.strftime("%Y%m%d%H%M") if latest else "000000"
        return f"v{count}.{hash_suffix}"
    except Exception:
        return "v0.fallback"
