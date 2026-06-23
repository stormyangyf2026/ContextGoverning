"""Agent consumption guidance service — generates structured consumption guidance for contexts.

Provides usage advice, cross-validation suggestions, and experience library markings
for Agent consumption of context items.
All configuration via Settings/env (no hardcoded values).
"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.context import ContextItem


class GuidanceService:
    """Generates Agent consumption guidance for context items."""

    # Confidence level to reference permission mapping
    CONFIDENCE_REFERENCE_TABLE = {
        "L0": {"can_reference": False, "reason": "数据未验证，不可引用"},
        "L1": {"can_reference": False, "reason": "数据未经交叉验证，不建议引用"},
        "L2": {"can_reference": True, "reason": "数据已验证，可谨慎引用", "hint": "引用时请标注来源"},
        "L3": {"can_reference": True, "reason": "多源印证数据，可正常引用", "hint": "引用时建议标注来源"},
        "L4": {"can_reference": True, "reason": "专家审核数据，可高频引用", "hint": "高可信度来源"},
        "L5": {"can_reference": True, "reason": "管理员确认数据，可完全信任引用", "hint": "最高可信度来源"},
    }

    def generate_guidance(
        self,
        ctx: ContextItem,
    ) -> Dict[str, Any]:
        """Generate consumption guidance for a single context item.

        Returns structured guidance with:
        - usage_advice: Whether and how to use this context
        - cross_validation_suggestion: Suggestions for cross-validation
        - experience_marks: If this is a lesson_learned context
        - lifecycle_warning: Warning about lifecycle status
        """
        conf_level = ctx.confidence_level or "L2"
        ref_info = self.CONFIDENCE_REFERENCE_TABLE.get(
            conf_level,
            {"can_reference": False, "reason": "未知置信度等级"},
        )

        guidance = {
            "context_id": ctx.context_id,
            "can_agent_reference": ref_info["can_reference"],
            "usage_advice": ref_info.get("reason", ""),
            "reference_hint": ref_info.get("hint", ""),
            "cross_validation_suggestion": self._get_cross_validation(ctx),
            "lifecycle_warning": self._get_lifecycle_warning(ctx),
            "experience_marks": self._get_experience_marks(ctx),
        }

        return guidance

    def _get_cross_validation(self, ctx: ContextItem) -> Optional[str]:
        """Suggest cross-validation strategy based on confidence."""
        level = ctx.confidence_level or "L2"
        if level in ("L0", "L1", "L2"):
            return f"建议与L3级以上来源交叉验证（当前等级：{level}）"
        return None

    def _get_lifecycle_warning(self, ctx: ContextItem) -> Optional[str]:
        """Generate lifecycle status warning."""
        status = ctx.lifecycle_status
        warnings = {
            "decaying": "该上下文正在衰减中，数据可能已过时",
            "contradicted": "该上下文存在矛盾数据，请参考相关矛盾上下文",
            "superseded": "该上下文已被更新版本替代，请使用最新版本",
            "needs_update": "该上下文需要更新，数据可能不完整",
            "archived": "该上下文已归档，仅供参考",
        }
        return warnings.get(status)

    def _get_experience_marks(self, ctx: ContextItem) -> Optional[Dict[str, Any]]:
        """Check if this is an experience/lesson-learned context."""
        if getattr(ctx, "confidence_source_type", None) == "lesson_learned":
            return {
                "is_lesson_learned": True,
                "context_role": getattr(ctx, "context_role", None),
                "structured_fields": getattr(ctx, "structured_fields", None),
            }
        return None

    def batch_generate(
        self,
        db: Session,
        contexts: list,
    ) -> Dict[str, Any]:
        """Generate guidance for multiple contexts at once."""
        results = []
        for ctx in contexts:
            results.append(self.generate_guidance(ctx))
        return {"guidance": results, "count": len(results)}


# Singleton
_guidance_service: Optional[GuidanceService] = None


def get_guidance_service() -> GuidanceService:
    global _guidance_service
    if _guidance_service is None:
        _guidance_service = GuidanceService()
    return _guidance_service
