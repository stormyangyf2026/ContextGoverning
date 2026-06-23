"""Internal API v1 — RLHF Classification Rule management endpoints."""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import get_db
from app.services.classification_learning_service import (
    get_rules, create_rule, update_rule, delete_rule,
    evaluate_rules, discover_new_keywords,
)

router = APIRouter(prefix="/classification-rules", tags=["classification-rules"])


# ── Schemas ────────────────────────────────────────────────────

class CreateRuleRequest(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=128)
    domain: str = Field(..., description="customer / project / operations / external")
    weight: float = Field(0.5, ge=0.0, le=1.0)
    sub_category: Optional[str] = None
    status: str = "active"


class UpdateRuleRequest(BaseModel):
    weight: Optional[float] = Field(None, ge=0.0, le=1.0)
    status: Optional[str] = None
    target_domain: Optional[str] = None


class ApplySuggestionsRequest(BaseModel):
    rule_ids: Optional[List[str]] = None  # specific rules to apply, or None for all
    min_weight: float = Field(0.3, ge=0.0, le=1.0)


# ── Rule CRUD ──────────────────────────────────────────────────

@router.get("/")
def list_rules(
    db: Session = Depends(get_db),
    domain: Optional[str] = None,
    status: Optional[str] = None,
    order_by: str = "weight",
    skip: int = 0,
    limit: int = 50,
):
    """List classification rules with filtering and sorting."""
    rules = get_rules(db, domain=domain, status=status, order_by=order_by, skip=skip, limit=limit)
    return [
        {
            "id": str(r.id),
            "rule_keyword": r.rule_keyword,
            "target_domain": r.target_domain,
            "target_sub_category": r.target_sub_category,
            "weight": r.weight,
            "precision": r.precision,
            "total_matches": r.total_matches,
            "correct_matches": r.correct_matches,
            "status": r.status,
            "source": r.source,
            "learned_from": r.learned_from,
            "last_corrected": str(r.last_corrected) if r.last_corrected else None,
        }
        for r in rules
    ]


@router.post("/", status_code=201)
def create_classification_rule(
    payload: CreateRuleRequest,
    db: Session = Depends(get_db),
):
    """Manually create a classification rule."""
    rule = create_rule(
        db,
        workspace_id=None,
        keyword=payload.keyword,
        domain=payload.domain,
        weight=payload.weight,
        sub_category=payload.sub_category,
        status=payload.status,
    )
    return {"id": str(rule.id), "rule_keyword": rule.rule_keyword, "target_domain": rule.target_domain}


@router.put("/{rule_id}")
def update_classification_rule(
    rule_id: str,
    payload: UpdateRuleRequest,
    db: Session = Depends(get_db),
):
    """Update a classification rule."""
    rule = update_rule(
        db, rule_id,
        weight=payload.weight,
        status=payload.status,
        target_domain=payload.target_domain,
    )
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"id": str(rule.id), "status": "updated"}


@router.delete("/{rule_id}")
def delete_classification_rule(rule_id: str, db: Session = Depends(get_db)):
    """Delete a classification rule."""
    success = delete_rule(db, rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"status": "deleted"}


# ── Rule Evaluation ────────────────────────────────────────────

@router.get("/evaluate")
def evaluate_classification_rules(db: Session = Depends(get_db)):
    """Evaluate current classification rule performance."""
    return evaluate_rules(db)


@router.get("/suggestions")
def get_rule_suggestions(
    db: Session = Depends(get_db),
    domain: Optional[str] = None,
    min_frequency: int = Query(2, ge=1, le=20),
):
    """Get system-suggested new rules or weight adjustments."""
    keywords = discover_new_keywords(db, min_frequency=min_frequency)
    if domain:
        keywords = [k for k in keywords if k["domain"] == domain]
    return {
        "suggestions": keywords[:10],
        "total_candidates": len(keywords),
    }


@router.post("/apply-suggestions")
def apply_rule_suggestions(
    payload: ApplySuggestionsRequest,
    db: Session = Depends(get_db),
):
    """Apply suggested rules."""
    keywords = discover_new_keywords(db, min_frequency=2)

    applied = 0
    for kw in keywords:
        if kw["weight"] < payload.min_weight:
            continue
        if payload.rule_ids and kw["keyword"] not in payload.rule_ids:
            continue
        create_rule(db, None, kw["keyword"], kw["domain"], kw["weight"], source="learned")
        applied += 1

    return {"applied": applied}


@router.get("/keywords/discover")
def discover_keywords_endpoint(
    db: Session = Depends(get_db),
    domain: Optional[str] = None,
    min_frequency: int = Query(3, ge=2, le=20),
):
    """Discover new candidate keywords from corrected contexts."""
    keywords = discover_new_keywords(db, min_frequency=min_frequency)
    if domain:
        keywords = [k for k in keywords if k["domain"] == domain]
    return {"candidates": keywords[:15]}
