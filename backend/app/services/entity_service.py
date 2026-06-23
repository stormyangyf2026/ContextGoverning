"""Entity service — NER entity extraction and CRUD management."""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.entity import Entity


def create_entity(
    db: Session,
    name: str,
    entity_type: str,
    domain: Optional[str] = None,
    aliases: Optional[List[str]] = None,
    metadata: Optional[dict] = None,
) -> Entity:
    """Create or get existing entity (idempotent by name+type)."""
    existing = (
        db.query(Entity)
        .filter(Entity.name == name, Entity.type == entity_type)
        .first()
    )
    if existing:
        return existing

    entity = Entity(
        name=name,
        type=entity_type,
        domain=domain,
        aliases=aliases or [],
        extra_data=metadata or {},
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity


def get_entity(db: Session, entity_id: str) -> Optional[Entity]:
    return db.query(Entity).filter(Entity.id == entity_id).first()


def list_entities(
    db: Session,
    entity_type: Optional[str] = None,
    domain: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[Entity]:
    query = db.query(Entity)
    if entity_type:
        query = query.filter(Entity.type == entity_type)
    if domain:
        query = query.filter(Entity.domain == domain)
    if search:
        query = query.filter(Entity.name.ilike(f"%{search}%"))
    return query.offset(skip).limit(limit).all()


def update_entity(
    db: Session,
    entity_id: str,
    name: Optional[str] = None,
    domain: Optional[str] = None,
    aliases: Optional[List[str]] = None,
    metadata: Optional[dict] = None,
) -> Entity:
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if entity is None:
        raise ValueError(f"Entity not found: {entity_id}")
    if name:
        entity.name = name
    if domain is not None:
        entity.domain = domain
    if aliases is not None:
        entity.aliases = aliases
    if metadata is not None:
        entity.extra_data = metadata
    db.commit()
    db.refresh(entity)
    return entity
