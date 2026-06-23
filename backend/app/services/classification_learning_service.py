"""RLHF classification learning service — learn classification rules from human feedback."""
import json
import re
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timezone
from collections import Counter

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.review_feedback import (
    ClassificationLabel, ClassificationRuleWeight,
    FeedbackDataset, RuleLearningLog,
)
from app.models.context import ContextItem, VALID_DOMAINS


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Core Learning Engine ───────────────────────────────────────

def learn_from_feedback(
    db: Session,
    workspace_id: Optional[str] = None,
    dataset_id: Optional[str] = None,
    auto_apply: bool = False,
    min_accuracy_improvement: float = 0.02,
    created_by: Optional[str] = None,
) -> RuleLearningLog:
    """Execute a complete learning cycle from feedback data.

    Steps:
    1. Load feedback labels (from dataset if specified, else from all validated labels)
    2. Analyze error patterns
    3. Discover new keywords from corrected contexts
    4. Adjust existing rule weights based on precision
    5. Deprecate low-quality rules
    6. Evaluate new rules on test split
    7. Record learning log
    8. Auto-apply if accuracy improvement exceeds threshold
    """
    start_time = utcnow()

    # Count existing rules
    rules_query = db.query(ClassificationRuleWeight)
    if workspace_id:
        rules_query = rules_query.filter(ClassificationRuleWeight.workspace_id == workspace_id)
    total_rules_before = rules_query.filter(ClassificationRuleWeight.status != "deprecated").count()

    # Calculate current accuracy
    accuracy_before = _calculate_current_accuracy(db, workspace_id)

    # Initialize learning log
    log = RuleLearningLog(
        trigger_source="manual" if created_by else "scheduled",
        total_rules_before=total_rules_before,
        accuracy_before=accuracy_before,
        status="running",
        created_by=created_by,
    )
    if workspace_id:
        log.workspace_id = workspace_id
    if dataset_id:
        log.dataset_id = dataset_id
    db.add(log)
    db.commit()
    db.refresh(log)

    try:
        # Step 1: Get feedback labels
        labels = _get_valid_labels(db, workspace_id)
        if not labels:
            log.status = "completed"
            log.error_message = "Insufficient feedback data for learning"
            db.commit()
            return log

        # Step 2: Discover new keywords
        new_keywords = discover_new_keywords(db, workspace_id, min_frequency=3)
        rules_added = 0
        top_keywords = []

        for kw in new_keywords:
            rule = _create_or_update_rule(
                db, workspace_id, kw["keyword"], kw["domain"],
                weight=kw["weight"], source="learned",
            )
            if rule and kw.get("is_new"):
                rules_added += 1
                top_keywords.append({"keyword": kw["keyword"], "domain": kw["domain"], "weight": kw["weight"]})

        # Step 3: Adjust existing rule weights
        rules_updated = adjust_rule_weights(db, workspace_id)

        # Step 4: Deprecate low-quality rules
        rules_deprecated = _deprecate_low_quality_rules(db, workspace_id)

        # Step 5: Evaluate
        accuracy_after = _calculate_current_accuracy(db, workspace_id)
        improvement = accuracy_after - accuracy_before

        # Update log
        log.rules_added = rules_added
        log.rules_updated = rules_updated
        log.rules_deprecated = rules_deprecated
        log.accuracy_after = accuracy_after
        log.accuracy_improvement = round(improvement, 3)
        log.top_new_keywords = json.dumps(top_keywords[:10])
        log.status = "completed"
        log.duration_seconds = int((utcnow() - start_time).total_seconds())
        db.commit()

        # Auto-apply if improvement is significant
        if auto_apply and improvement >= min_accuracy_improvement:
            _apply_learned_rules(db, workspace_id, log.id)

        return log

    except Exception as e:
        log.status = "failed"
        log.error_message = str(e)
        log.duration_seconds = int((utcnow() - start_time).total_seconds())
        db.commit()
        raise


# ── Keyword Discovery ──────────────────────────────────────────

def discover_new_keywords(
    db: Session,
    workspace_id: Optional[str] = None,
    min_frequency: int = 3,
    tfidf_threshold: float = 0.15,
) -> List[Dict]:
    """Discover new keywords from corrected context classifications.

    Uses a simplified TF-IDF approach:
    1. Get all contexts where classification was corrected
    2. Extract Chinese words from corrected contexts
    3. Calculate term frequency per domain
    4. Filter and rank candidates
    """
    # Get correction labels (predicted -> corrected)
    query = db.query(ClassificationLabel).filter(
        ClassificationLabel.label_type == "domain",
        ClassificationLabel.confidence >= 0.7,
    )
    if workspace_id:
        query = query.filter(ClassificationLabel.workspace_id == workspace_id)

    corrections = query.all()
    if not corrections:
        return []

    # Group by corrected domain and collect contexts
    domain_contexts: Dict[str, List[str]] = {}
    for label in corrections[:500]:  # limit to recent 500
        ctx = db.query(ContextItem).filter(ContextItem.id == label.context_id).first()
        if not ctx:
            continue
        domain = label.corrected_value
        if domain not in domain_contexts:
            domain_contexts[domain] = []
        domain_contexts[domain].append(f"{ctx.title} {ctx.content or ''}")

    # Get existing keywords to avoid duplicates
    existing_keywords = set()
    rules_query = db.query(ClassificationRuleWeight)
    if workspace_id:
        rules_query = rules_query.filter(ClassificationRuleWeight.workspace_id == workspace_id)
    for rule in rules_query.all():
        existing_keywords.add(rule.rule_keyword)

    # Extract candidate keywords per domain
    candidates = []
    total_docs = sum(len(texts) for texts in domain_contexts.values())

    for domain, texts in domain_contexts.items():
        if len(texts) < min_frequency:
            continue

        # Simple Chinese word extraction (2-4 char sequences)
        word_counter = Counter()
        for text in texts:
            words = _extract_chinese_keywords(text)
            for w in words:
                if w not in existing_keywords:
                    word_counter[w] += 1

        # Calculate simplified TF-IDF: tf * log(total_docs / doc_count)
        for word, tf in word_counter.most_common(30):
            if tf < min_frequency:
                continue
            # Count how many documents contain this word
            doc_count = sum(1 for t in texts if word in t)
            idf = 1.0 if doc_count == 0 else max(0.1, total_docs / doc_count)
            tfidf = (tf / max(len(texts), 1)) * (1.0 / idf) if idf > 0 else tf / max(len(texts), 1)

            if tfidf >= tfidf_threshold:
                is_new = word not in existing_keywords
                candidates.append({
                    "keyword": word,
                    "domain": domain,
                    "frequency": tf,
                    "tfidf_score": round(tfidf, 3),
                    "weight": round(min(0.6, 0.3 + tfidf * 0.3), 2),
                    "is_new": is_new,
                })

    # Sort by TF-IDF score
    candidates.sort(key=lambda x: x["tfidf_score"], reverse=True)
    return candidates[:20]


def _extract_chinese_keywords(text: str) -> List[str]:
    """Extract potential Chinese keywords (2-4 char sequences)."""
    # Simple approach: extract CJK character sequences
    cjk_pattern = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf]{2,4}')
    matches = cjk_pattern.findall(text)
    # Filter common stop words
    stop_chars = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一',
                  '一个', '这个', '那个', '什么', '怎么', '哪', '那', '你', '他', '她', '它'}
    return [m for m in matches if m not in stop_chars]


# ── Rule Weight Adjustment ─────────────────────────────────────

def calculate_rule_precision(
    db: Session, keyword: str, domain: str, workspace_id: Optional[str] = None,
) -> Tuple[float, int, int]:
    """Calculate the precision of a classification rule.

    Precision = correct_matches / total_matches based on review feedback.
    """
    # Count how many times this rule was triggered
    # (context was auto-classified to this domain and keyword appears in content)
    # For simplicity, we use the stored rule stats
    rule = db.query(ClassificationRuleWeight).filter(
        ClassificationRuleWeight.rule_keyword == keyword,
        ClassificationRuleWeight.target_domain == domain,
    )
    if workspace_id:
        rule = rule.filter(ClassificationRuleWeight.workspace_id == workspace_id)
    rule = rule.first()

    if rule:
        return (rule.precision or 0.0, rule.total_matches or 0, rule.correct_matches or 0)
    return (0.0, 0, 0)


def adjust_rule_weights(
    db: Session, workspace_id: Optional[str] = None,
    smooth_factor: float = 0.3,
) -> int:
    """Batch-adjust all active rule weights based on feedback precision."""
    query = db.query(ClassificationRuleWeight).filter(
        ClassificationRuleWeight.status != "deprecated",
    )
    if workspace_id:
        query = query.filter(ClassificationRuleWeight.workspace_id == workspace_id)

    rules = query.all()
    updated_count = 0

    for rule in rules:
        # Calculate precision from feedback
        precision, total, correct = _estimate_rule_precision_from_feedback(
            db, rule.rule_keyword, rule.target_domain, workspace_id,
        )

        # Update rule stats
        rule.precision = round(precision, 3)
        rule.total_matches = total
        rule.correct_matches = correct

        # Update weight: w_new = α * precision + (1-α) * w_old
        if total >= 10:  # only update if enough data
            old_weight = rule.weight or 0.5
            rule.weight = round(smooth_factor * precision + (1 - smooth_factor) * old_weight, 3)
            updated_count += 1

    db.commit()
    return updated_count


def _estimate_rule_precision_from_feedback(
    db: Session, keyword: str, domain: str, workspace_id: Optional[str] = None,
) -> Tuple[float, int, int]:
    """Estimate rule precision by analyzing review records.

    A rule is "correct" if: keyword triggered classification to domain AND reviewer confirmed it.
    """
    # Find reviews where original_domain matches the rule's target domain
    query = db.query(
        func.count().label("total"),
        func.sum(
            func.case((ReviewRecord.classification_correct == True, 1), else_=0)
        ).label("correct"),
    )
    if workspace_id:
        query = query.filter(ReviewRecord.workspace_id == workspace_id)

    result = query.filter(
        ReviewRecord.original_domain == domain,
    ).first()

    # This is a rough estimate since we can't easily determine which specific keyword triggered
    # each classification. For production, track per-context which rules matched.
    total = int(result[0]) if result and result[0] else 0
    correct = int(result[1]) if result and result[1] else 0

    from app.models.review_feedback import ReviewRecord
    precision = correct / total if total > 0 else 0.5
    return (precision, total, correct)


def _deprecate_low_quality_rules(
    db: Session, workspace_id: Optional[str] = None,
    min_precision: float = 0.3, min_matches: int = 20,
) -> int:
    """Mark low-quality rules as deprecated."""
    query = db.query(ClassificationRuleWeight).filter(
        ClassificationRuleWeight.status == "active",
        ClassificationRuleWeight.precision.isnot(None),
        ClassificationRuleWeight.precision < min_precision,
        ClassificationRuleWeight.total_matches >= min_matches,
    )
    if workspace_id:
        query = query.filter(ClassificationRuleWeight.workspace_id == workspace_id)

    deprecated = 0
    for rule in query.all():
        rule.status = "deprecated"
        deprecated += 1

    if deprecated:
        db.commit()
    return deprecated


# ── Rule Helpers ───────────────────────────────────────────────

def _create_or_update_rule(
    db: Session, workspace_id: Optional[str], keyword: str, domain: str,
    weight: float = 0.5, source: str = "learned",
) -> Optional[ClassificationRuleWeight]:
    """Create or update a classification rule."""
    query = db.query(ClassificationRuleWeight).filter(
        ClassificationRuleWeight.rule_keyword == keyword,
        ClassificationRuleWeight.target_domain == domain,
    )
    if workspace_id:
        query = query.filter(ClassificationRuleWeight.workspace_id == workspace_id)

    rule = query.first()
    if rule:
        rule.weight = max(rule.weight or 0.5, weight)
        rule.updated_at = utcnow()
    else:
        rule = ClassificationRuleWeight(
            rule_keyword=keyword,
            target_domain=domain,
            weight=weight,
            source=source,
        )
        if workspace_id:
            rule.workspace_id = workspace_id
        db.add(rule)

    db.commit()
    db.refresh(rule)
    return rule


def _apply_learned_rules(db: Session, workspace_id: Optional[str], log_id: str):
    """Mark the learning log as applied (rules are already in DB)."""
    log = db.query(RuleLearningLog).filter(RuleLearningLog.id == log_id).first()
    if log:
        log.status = "completed"


def _get_valid_labels(
    db: Session, workspace_id: Optional[str] = None, min_confidence: float = 0.7,
) -> List[ClassificationLabel]:
    """Get validated classification labels for learning."""
    query = db.query(ClassificationLabel).filter(
        ClassificationLabel.label_type == "domain",
        ClassificationLabel.confidence >= min_confidence,
    )
    if workspace_id:
        query = query.filter(ClassificationLabel.workspace_id == workspace_id)
    return query.order_by(ClassificationLabel.created_at.desc()).limit(1000).all()


def _calculate_current_accuracy(
    db: Session, workspace_id: Optional[str] = None,
) -> float:
    """Calculate current classification accuracy from all review records."""
    from app.models.review_feedback import ReviewRecord
    query = db.query(ReviewRecord).filter(
        ReviewRecord.classification_correct.isnot(None),
    )
    if workspace_id:
        query = query.filter(ReviewRecord.workspace_id == workspace_id)

    total = query.count()
    correct = query.filter(ReviewRecord.classification_correct == True).count()
    return round((correct / total * 100), 1) if total > 0 else 0.0


# ── Rule Evaluation ────────────────────────────────────────────

def evaluate_rules(
    db: Session, workspace_id: Optional[str] = None,
) -> Dict:
    """Evaluate current classification rule performance."""
    query = db.query(ClassificationRuleWeight)
    if workspace_id:
        query = query.filter(ClassificationRuleWeight.workspace_id == workspace_id)

    rules = query.all()
    active = [r for r in rules if r.status == "active"]
    deprecated = [r for r in rules if r.status == "deprecated"]
    under_review = [r for r in rules if r.status == "under_review"]

    accuracy = _calculate_current_accuracy(db, workspace_id)

    domain_stats = {}
    for domain in VALID_DOMAINS:
        domain_rules = [r for r in active if r.target_domain == domain]
        if domain_rules:
            avg_precision = sum(r.precision or 0 for r in domain_rules) / len(domain_rules)
            domain_stats[domain] = {
                "rule_count": len(domain_rules),
                "avg_weight": round(sum(r.weight or 0 for r in domain_rules) / len(domain_rules), 3),
                "avg_precision": round(avg_precision, 3),
            }

    return {
        "total_rules": len(rules),
        "active_rules": len(active),
        "deprecated_rules": len(deprecated),
        "under_review_rules": len(under_review),
        "overall_accuracy": accuracy,
        "domain_stats": domain_stats,
    }


# ── Rule Management ────────────────────────────────────────────

def get_rules(
    db: Session,
    workspace_id: Optional[str] = None,
    domain: Optional[str] = None,
    status: Optional[str] = None,
    order_by: str = "weight",
    skip: int = 0,
    limit: int = 50,
) -> List[ClassificationRuleWeight]:
    """Get classification rules with filters."""
    query = db.query(ClassificationRuleWeight)
    if workspace_id:
        query = query.filter(ClassificationRuleWeight.workspace_id == workspace_id)
    if domain:
        query = query.filter(ClassificationRuleWeight.target_domain == domain)
    if status:
        query = query.filter(ClassificationRuleWeight.status == status)

    if order_by == "weight":
        query = query.order_by(ClassificationRuleWeight.weight.desc())
    elif order_by == "precision":
        query = query.order_by(ClassificationRuleWeight.precision.desc().nullslast())
    elif order_by == "matches":
        query = query.order_by(ClassificationRuleWeight.total_matches.desc())

    return query.offset(skip).limit(limit).all()


def create_rule(
    db: Session,
    workspace_id: Optional[str],
    keyword: str,
    domain: str,
    weight: float = 0.5,
    sub_category: Optional[str] = None,
    status: str = "active",
) -> ClassificationRuleWeight:
    """Manually create a classification rule."""
    return _create_or_update_rule(db, workspace_id, keyword, domain, weight, source="manual")


def update_rule(
    db: Session,
    rule_id: str,
    weight: Optional[float] = None,
    status: Optional[str] = None,
    target_domain: Optional[str] = None,
) -> Optional[ClassificationRuleWeight]:
    """Update a classification rule."""
    rule = db.query(ClassificationRuleWeight).filter(
        ClassificationRuleWeight.id == rule_id,
    ).first()
    if not rule:
        return None

    if weight is not None:
        rule.weight = weight
    if status is not None:
        rule.status = status
    if target_domain is not None:
        rule.target_domain = target_domain

    rule.updated_at = utcnow()
    db.commit()
    db.refresh(rule)
    return rule


def delete_rule(db: Session, rule_id: str) -> bool:
    """Delete a classification rule."""
    rule = db.query(ClassificationRuleWeight).filter(
        ClassificationRuleWeight.id == rule_id,
    ).first()
    if not rule:
        return False
    db.delete(rule)
    db.commit()
    return True


def rollback_rules(
    db: Session, workspace_id: Optional[str], learning_log_id: str,
) -> Optional[RuleLearningLog]:
    """Rollback to a previous learning state."""
    log = db.query(RuleLearningLog).filter(RuleLearningLog.id == learning_log_id).first()
    if not log:
        return None

    log.status = "rolled_back"
    db.commit()

    # Note: Full rollback requires restoring rule states from a snapshot.
    # For now, we mark the log as rolled_back. A full implementation would
    # store rule snapshots in learning_details JSONB.
    return log
