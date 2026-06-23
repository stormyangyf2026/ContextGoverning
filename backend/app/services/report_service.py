"""Report generation service — template-based context report generation.

Provides report template filling and context injection for automated reporting.
All configuration via Settings/env (no hardcoded values).
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models.context import ContextItem


class ReportService:
    """Template-based context report generation."""

    def generate_report(
        self,
        db: Session,
        template_type: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate a report by filling a template with context data.

        Args:
            db: Database session
            template_type: Report template type (summary, detailed, entity_overview)
            parameters: Optional parameters for filtering/formatting

        Returns:
            Report dict with title, sections, contexts, and metadata
        """
        parameters = parameters or {}
        domain = parameters.get("domain")
        entity_name = parameters.get("entity_name")

        # Query relevant contexts
        conditions = [ContextItem.is_deleted == False]
        if domain:
            conditions.append(ContextItem.domain == domain)

        contexts = (
            db.query(ContextItem)
            .filter(*conditions)
            .order_by(ContextItem.created_at.desc())
            .limit(parameters.get("limit", 50))
            .all()
        )

        if template_type == "entity_overview" and entity_name:
            contexts = self._filter_by_entity(db, contexts, entity_name)

        title = self._get_title(template_type, parameters)
        sections = self._build_sections(template_type, contexts, parameters)

        return {
            "title": title,
            "generated_at": __import__("datetime").datetime.now().isoformat(),
            "template_type": template_type,
            "sections": sections,
            "context_count": len(contexts),
            "metadata": {
                "domain": domain,
                "entity": entity_name,
                "parameters": parameters,
            },
        }

    def _get_title(self, template_type: str, params: Dict[str, Any]) -> str:
        titles = {
            "summary": "上下文摘要报告",
            "detailed": "上下文详细报告",
            "entity_overview": f"实体概览报告 - {params.get('entity_name', '全部')}",
        }
        return titles.get(template_type, "上下文报告")

    def _build_sections(
        self,
        template_type: str,
        contexts: List[ContextItem],
        params: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        sections = []

        # Summary section
        sections.append({
            "heading": "概览",
            "content": f"共 {len(contexts)} 条上下文记录",
        })

        # Context list section
        context_items = []
        for ctx in contexts:
            context_items.append({
                "id": ctx.context_id,
                "title": ctx.title,
                "domain": ctx.domain,
                "confidence_level": ctx.confidence_level,
                "lifecycle_status": ctx.lifecycle_status,
                "created_at": ctx.created_at.isoformat() if ctx.created_at else None,
            })

        sections.append({
            "heading": "上下文列表",
            "contexts": context_items,
        })

        return sections

    def _filter_by_entity(
        self,
        db: Session,
        contexts: List[ContextItem],
        entity_name: str,
    ) -> List[ContextItem]:
        """Filter contexts by associated entity name."""
        from app.models.context_entity import ContextEntityMap
        from app.models.entity import Entity

        entity = db.query(Entity).filter(Entity.name == entity_name).first()
        if not entity:
            return contexts

        context_ids = set(c.id for c in contexts)
        maps = (
            db.query(ContextEntityMap)
            .filter(
                ContextEntityMap.entity_id == entity.id,
                ContextEntityMap.context_id.in_(context_ids),
            )
            .all()
        )
        allowed_ids = {m.context_id for m in maps}
        return [c for c in contexts if c.id in allowed_ids]


# Singleton
_report_service: Optional[ReportService] = None


def get_report_service() -> ReportService:
    global _report_service
    if _report_service is None:
        _report_service = ReportService()
    return _report_service
