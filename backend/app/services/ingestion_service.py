"""Ingestion service — unified entry point for all data collection pipelines.

Coordinates: dedup → classification → entity extraction → relation detection →
    confidence evaluation → conflict detection → save to DB.
"""
from typing import Optional
from sqlalchemy.orm import Session

from app.models.context import ContextItem
from app.services.context_service import create_context
from app.services.classification_service import classify_domain, classify_sub_category, get_rule_version
from app.services.confidence_service import get_initial_confidence
from app.services.entity_service import create_entity
from app.services.relation_service import create_relation
from datetime import datetime, timezone


def ingest_context(
    db: Session,
    actor: str,
    title: str,
    content: str,
    context_id: str,
    source_system: str,
    source_type: str,
    source_url: Optional[str] = None,
    source_platform: Optional[str] = None,
    context_subtype: Optional[str] = None,
    context_role: Optional[str] = None,
    structured_fields: Optional[dict] = None,
    entities: Optional[list[dict]] = None,
) -> ContextItem:
    """Unified ingestion pipeline entry point.

    Args:
        db: Database session
        actor: Who/what triggered the ingestion (username or system name)
        title: Context title
        content: Context content
        context_id: Unique human-readable ID
        source_system: E.g., project_kb, memory_md, feishu, email, manual
        source_type: Confidence source type (e.g., project_kb, memory_md)
        source_url: Optional URL of the source
        source_platform: Platform identifier (e.g., ima, feishu_drive)
        context_subtype: Optional subtype (e.g., lesson_learned)
        context_role: Optional role from Memory.md template (goal/progress/finding/lesson_learned)
        structured_fields: Optional JSONB structured data
        entities: List of {name, type, domain, role} dicts to link

    Returns:
        The created ContextItem.
    """
    # 1. Classification (DB-driven with fallback)
    domain, classification_source = classify_domain(title, content, db=db)
    sub_category = classify_sub_category(domain, content)

    # 2. Confidence
    confidence_level, confidence_score = get_initial_confidence(source_type)

    # 3. Create context
    ctx = create_context(
        db=db,
        actor=actor,
        title=title,
        content=content,
        domain=domain,
        context_id=context_id,
        source_system=source_system,
        confidence_level=confidence_level,
        confidence_score=confidence_score,
        confidence_source_type=source_type,
        context_subtype=context_subtype,
        context_role=context_role,
        structured_fields=structured_fields,
    )

    # 4. Set additional fields including RLHF classification tracking
    ctx.sub_category = sub_category
    ctx.source_url = source_url
    ctx.source_platform = source_platform
    ctx.classification_source = classification_source
    ctx.classification_rule_version = get_rule_version(db)
    ctx.last_classified_at = datetime.now(timezone.utc)

    # 5. Entity linking
    if entities:
        for ent in entities:
            entity = create_entity(
                db=db,
                name=ent["name"],
                entity_type=ent.get("type", "unknown"),
                domain=domain,
            )
            from app.models.context_entity import ContextEntityMap
            link = ContextEntityMap(
                context_id=ctx.id,
                entity_id=entity.id,
                role=ent.get("role", "mention"),
            )
            db.add(link)

    db.commit()
    db.refresh(ctx)
    return ctx
