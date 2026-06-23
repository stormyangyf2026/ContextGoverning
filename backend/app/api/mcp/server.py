"""MCP Server — Agent tools for context platform integration.

Provides 8 MCP tools that Agents can call to search, retrieve, and submit context.
All configuration via Settings/env (no hardcoded values).
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.services.search_service import get_search_service
from app.services.graph_service import get_graph_service
from app.services.guidance_service import get_guidance_service
from app.services.context_service import create_context, get_context


class MCPServer:
    """MCP (Model Context Protocol) Server with 8 tools for Agent integration."""

    def search_context(
        self,
        db: Session,
        query: str,
        mode: str = "hybrid",
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Tool: search_context — Search for relevant context with consumption guidance."""
        search_svc = get_search_service()
        results = search_svc.search(
            db, query, mode=mode, filters=filters,
            page=1, page_size=top_k,
            include_confidence_detail=True,
        )

        guidance_svc = get_guidance_service()
        for item in results.get("data", []):
            ctx = get_context(db, item["context_id"])
            if ctx:
                item["consumption_guidance"] = guidance_svc.generate_guidance(ctx)

        return results

    def get_context_detail(
        self,
        db: Session,
        context_id: str,
    ) -> Dict[str, Any]:
        """Tool: get_context_detail — Get full context detail with consumption guidance."""
        ctx = get_context(db, context_id)
        if not ctx:
            return {"error": "Context not found", "context_id": context_id}

        guidance_svc = get_guidance_service()
        guidance = guidance_svc.generate_guidance(ctx)

        return {
            "context_id": ctx.context_id,
            "title": ctx.title,
            "content": ctx.content,
            "domain": ctx.domain,
            "confidence_level": ctx.confidence_level,
            "confidence_score": ctx.confidence_score,
            "lifecycle_status": ctx.lifecycle_status,
            "consumption_guidance": guidance,
            "created_at": ctx.created_at.isoformat() if ctx.created_at else None,
            "created_by": ctx.created_by,
        }

    def get_entity_graph(
        self,
        db: Session,
        entity_name: str,
        depth: int = 2,
    ) -> Dict[str, Any]:
        """Tool: get_entity_graph — Get entity-centric knowledge graph subgraph."""
        graph_svc = get_graph_service()
        return graph_svc.get_subgraph(db, entity_name=entity_name, depth=depth)

    def get_context_timeline(
        self,
        db: Session,
        entity_name: Optional[str] = None,
        domain: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Tool: get_context_timeline — Get time-ordered context timeline."""
        from app.models.context import ContextItem

        conditions = [ContextItem.is_deleted == False]
        if domain:
            conditions.append(ContextItem.domain == domain)

        results = (
            db.query(ContextItem)
            .filter(*conditions)
            .order_by(ContextItem.created_at.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "id": ctx.context_id,
                "title": ctx.title,
                "domain": ctx.domain,
                "confidence_level": ctx.confidence_level,
                "created_at": ctx.created_at.isoformat() if ctx.created_at else None,
            }
            for ctx in results
        ]

    def get_contradictions(
        self,
        db: Session,
        domain: Optional[str] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Tool: get_contradictions — Get contexts with contradictory status."""
        from app.models.context import ContextItem

        conditions = [
            ContextItem.is_deleted == False,
            ContextItem.lifecycle_status == "contradicted",
        ]
        if domain:
            conditions.append(ContextItem.domain == domain)

        results = db.query(ContextItem).filter(*conditions).limit(limit).all()
        return {
            "contradictions": [
                {"context_id": ctx.context_id, "title": ctx.title, "domain": ctx.domain}
                for ctx in results
            ],
            "count": len(results),
        }

    def submit_context(
        self,
        db: Session,
        title: str,
        content: str,
        domain: str = "operations",
        created_by: str = "mcp_agent",
    ) -> Dict[str, Any]:
        """Tool: submit_context — Submit new context from Agent."""
        import uuid as uuid_lib
        try:
            ctx = create_context(
                db,
                actor=created_by,
                title=title,
                content=content,
                domain=domain,
                context_id=f"ctx_{uuid_lib.uuid4().hex[:12]}",
                confidence_source_type="agent_submission",
            )
            return {
                "status": "success",
                "context_id": ctx.context_id,
                "message": "Context submitted for review",
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def check_confidence(
        self,
        db: Session,
        context_id: str,
    ) -> Dict[str, Any]:
        """Tool: check_confidence — Check confidence level of a context."""
        ctx = get_context(db, context_id)
        if not ctx:
            return {"error": "Context not found"}

        guidance_svc = get_guidance_service()
        guidance = guidance_svc.generate_guidance(ctx)

        return {
            "context_id": ctx.context_id,
            "confidence_level": ctx.confidence_level,
            "confidence_score": ctx.confidence_score,
            "can_reference": guidance["can_agent_reference"],
            "consumption_guidance": guidance,
        }

    def submit_correction(
        self,
        db: Session,
        context_id: str,
        correction: str,
        submitted_by: str = "mcp_agent",
    ) -> Dict[str, Any]:
        """Tool: submit_correction — Submit correction/suggestion for a context."""
        import uuid as uuid_lib
        ctx = get_context(db, context_id)
        if not ctx:
            return {"error": "Context not found"}

        try:
            new_ctx = create_context(
                db,
                actor=submitted_by,
                title=f"[修正] {ctx.title}",
                content=correction,
                domain=ctx.domain,
                context_id=f"ctx_{uuid_lib.uuid4().hex[:12]}",
                confidence_source_type="manual_entry",
            )
            from app.services.lifecycle_service import transition
            transition(db, actor=submitted_by, context=ctx, new_status="needs_update")

            return {
                "status": "success",
                "original_context_id": context_id,
                "correction_context_id": new_ctx.context_id,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}


# Singleton
_mcp_server: Optional[MCPServer] = None


def get_mcp_server() -> MCPServer:
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = MCPServer()
    return _mcp_server
