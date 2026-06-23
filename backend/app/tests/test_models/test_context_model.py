"""Model validation tests — verify ORM field constraints and defaults."""
import pytest
from app.models.context import ContextItem, VALID_DOMAINS, VALID_LIFECYCLE_STATUSES, VALID_CONFIDENCE_LEVELS
from app.models.entity import Entity
from app.models.relation import Relation, VALID_RELATION_TYPES


class TestContextItemModel:
    def test_valid_domains(self):
        assert len(VALID_DOMAINS) == 4
        assert "customer" in VALID_DOMAINS
        assert "project" in VALID_DOMAINS

    def test_valid_lifecycle_statuses(self):
        assert len(VALID_LIFECYCLE_STATUSES) == 8
        assert "created" in VALID_LIFECYCLE_STATUSES
        assert "archived" in VALID_LIFECYCLE_STATUSES

    def test_valid_confidence_levels(self):
        assert len(VALID_CONFIDENCE_LEVELS) == 6
        assert "L0" in VALID_CONFIDENCE_LEVELS
        assert "L5" in VALID_CONFIDENCE_LEVELS

    def test_context_defaults(self, db):
        """Verify default values are set correctly."""
        ctx = ContextItem(
            context_id="ctx_defaults_test",
            title="默认值测试",
            content="测试默认值的内容",
            content_hash="hash123",
            domain="operations",
            created_by="test",
        )
        db.add(ctx)
        db.commit()
        assert ctx.confidence_level == "L2"
        assert ctx.confidence_score == 0.5
        assert ctx.lifecycle_status == "pending_review"
        assert ctx.is_immutable is False
        assert ctx.version == 1
        assert ctx.is_deleted is False
        assert ctx.relevance_score == 0.0


class TestEntityModel:
    def test_entity_defaults(self, db):
        entity = Entity(name="测试", type="project")
        db.add(entity)
        db.commit()
        assert entity.aliases == []
        assert entity.extra_data == {}


class TestRelationModel:
    def test_valid_relation_types(self):
        assert "drives" in VALID_RELATION_TYPES
        assert "depends_on" in VALID_RELATION_TYPES
        assert "contradicts" in VALID_RELATION_TYPES
        assert "supersedes" in VALID_RELATION_TYPES
        assert "threatens" in VALID_RELATION_TYPES
        assert "informs" in VALID_RELATION_TYPES
        assert "part_of" in VALID_RELATION_TYPES
        assert len(VALID_RELATION_TYPES) == 7
