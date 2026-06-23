"""Knowledge graph query service — entity/relation-based graph traversal.

Provides subgraph queries, entity-level aggregation, and 2-hop traversal.
All configuration via Settings/env (no hardcoded values).
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models.entity import Entity
from app.models.relation import Relation
from app.models.context_entity import ContextEntityMap
from app.models.context import ContextItem


class GraphService:
    """Knowledge graph query and traversal service."""

    def get_subgraph(
        self,
        db: Session,
        entity_id: Optional[str] = None,
        entity_name: Optional[str] = None,
        depth: int = 2,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Get entity-centric subgraph.

        Args:
            db: Database session
            entity_id: Entity UUID to center on
            entity_name: Entity name to center on (alternative)
            depth: Traversal depth (1 or 2)
            limit: Max nodes to return

        Returns:
            {"center_entity": {...}, "nodes": [...], "edges": [...]}
        """
        entity = None
        if entity_id:
            entity = db.query(Entity).filter(
                Entity.id == entity_id, Entity.id.isnot(None)
            ).first()
        elif entity_name:
            entity = db.query(Entity).filter(Entity.name == entity_name).first()

        if not entity:
            return {"center_entity": None, "nodes": [], "edges": []}

        # Get context-entity mappings for this entity
        context_maps = (
            db.query(ContextEntityMap)
            .filter(ContextEntityMap.entity_id == entity.id)
            .all()
        )
        context_ids = [cm.context_id for cm in context_maps]

        # Get related contexts
        contexts = (
            db.query(ContextItem)
            .filter(
                ContextItem.id.in_(context_ids),
                ContextItem.is_deleted == False,
            )
            .all()
        ) if context_ids else []

        # Get relations between these contexts
        edges = []
        if len(context_ids) >= 2:
            relations = (
                db.query(Relation)
                .filter(
                    Relation.source_id.in_(context_ids),
                    Relation.target_id.in_(context_ids),
                )
                .limit(limit)
                .all()
            )
            for rel in relations:
                edges.append({
                    "source_id": str(rel.source_id),
                    "target_id": str(rel.target_id),
                    "type": rel.relation_type,
                })

        # If depth >= 2, get related entities via the contexts
        related_entities = []
        if depth >= 2 and context_ids:
            related_maps = (
                db.query(ContextEntityMap)
                .filter(
                    ContextEntityMap.context_id.in_(context_ids),
                    ContextEntityMap.entity_id != entity.id,
                )
                .distinct(ContextEntityMap.entity_id)
                .limit(limit)
                .all()
            )
            related_entity_ids = [rm.entity_id for rm in related_maps]
            if related_entity_ids:
                related_entities = (
                    db.query(Entity)
                    .filter(Entity.id.in_(related_entity_ids))
                    .all()
                )

        # Build nodes
        nodes = [
            {
                "id": str(entity.id),
                "name": entity.name,
                "type": entity.type,
                "is_center": True,
            }
        ]
        for ctx in contexts:
            nodes.append({
                "id": str(ctx.id),
                "name": ctx.title,
                "type": "context",
                "is_center": False,
            })
        for re_entity in related_entities:
            nodes.append({
                "id": str(re_entity.id),
                "name": re_entity.name,
                "type": re_entity.type,
                "is_center": False,
            })

        return {
            "center_entity": {
                "id": str(entity.id),
                "name": entity.name,
                "type": entity.type,
                "domain": entity.domain,
            },
            "nodes": nodes,
            "edges": edges,
        }

    def get_entity_graph(
        self,
        db: Session,
        entity_name: str,
        depth: int = 2,
    ) -> Dict[str, Any]:
        """Get entity-centric graph by entity name. Alias for get_subgraph."""
        return self.get_subgraph(db, entity_name=entity_name, depth=depth)

    def get_context_relations(
        self,
        db: Session,
        context_id: str,
    ) -> List[Dict[str, str]]:
        """Get all relations for a specific context."""
        relations = (
            db.query(Relation)
            .filter(
                (Relation.source_id == context_id) |
                (Relation.target_id == context_id)
            )
            .all()
        )
        return [
            {
                "id": str(rel.id),
                "source_id": str(rel.source_id),
                "target_id": str(rel.target_id),
                "type": rel.relation_type,
                "direction": rel.direction,
            }
            for rel in relations
        ]


# Singleton
_graph_service: Optional[GraphService] = None


def get_graph_service() -> GraphService:
    global _graph_service
    if _graph_service is None:
        _graph_service = GraphService()
    return _graph_service
