"""Relation service — manages 7 relationship types between contexts."""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.relation import Relation, VALID_RELATION_TYPES


def create_relation(
    db: Session,
    source_id: str,
    target_id: str,
    relation_type: str,
    created_by: str,
    direction: str = "forward",
    metadata: Optional[dict] = None,
) -> Relation:
    """Create a relation between two contexts."""
    if relation_type not in VALID_RELATION_TYPES:
        raise ValueError(f"Invalid relation type: {relation_type}")

    if source_id == target_id:
        raise ValueError("Self-referencing relations are not allowed")

    relation = Relation(
        source_id=source_id,
        target_id=target_id,
        relation_type=relation_type,
        direction=direction,
        created_by=created_by,
        extra_data=metadata or {},
    )
    db.add(relation)
    db.commit()
    db.refresh(relation)
    return relation


def get_relation(db: Session, relation_id: str) -> Optional[Relation]:
    return db.query(Relation).filter(Relation.id == relation_id).first()


def list_relations(
    db: Session,
    context_id: Optional[str] = None,
    relation_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[Relation]:
    """List relations. If context_id provided, returns all relations for that node."""
    query = db.query(Relation)
    if context_id:
        query = query.filter(
            (Relation.source_id == context_id) | (Relation.target_id == context_id)
        )
    if relation_type:
        query = query.filter(Relation.relation_type == relation_type)
    return query.offset(skip).limit(limit).all()


def list_relations_by_type(
    db: Session, relation_type: str, skip: int = 0, limit: int = 50
) -> List[Relation]:
    if relation_type not in VALID_RELATION_TYPES:
        raise ValueError(f"Invalid relation type: {relation_type}")
    return (
        db.query(Relation)
        .filter(Relation.relation_type == relation_type)
        .offset(skip)
        .limit(limit)
        .all()
    )


def delete_relation(db: Session, relation_id: str) -> None:
    relation = db.query(Relation).filter(Relation.id == relation_id).first()
    if relation is None:
        raise ValueError(f"Relation not found: {relation_id}")
    db.delete(relation)
    db.commit()
