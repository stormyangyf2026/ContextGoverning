"""Unit tests for relation service."""
import pytest
from app.services.relation_service import (
    create_relation, get_relation, list_relations,
    list_relations_by_type, delete_relation,
)


class TestCreateRelation:
    def test_create_basic_relation(self, db, sample_context):
        """Create a relation between two contexts."""
        from app.models.context import ContextItem
        ctx2 = ContextItem(
            context_id="ctx_test_002",
            title="目标上下文",
            content="目标内容",
            content_hash="xyz789",
            domain="operations",
            lifecycle_status="active",
            created_by="test",
        )
        db.add(ctx2)
        db.commit()

        rel = create_relation(
            db, sample_context.id, ctx2.id,
            relation_type="depends_on", created_by="admin_test",
        )
        assert rel.relation_type == "depends_on"
        assert rel.source_id == sample_context.id
        assert rel.target_id == ctx2.id

    def test_invalid_relation_type_raises(self, db, sample_context):
        with pytest.raises(ValueError, match="Invalid relation type"):
            create_relation(
                db, sample_context.id, sample_context.id,
                relation_type="invalid_type", created_by="admin_test",
            )

    def test_self_referencing_raises(self, db, sample_context):
        with pytest.raises(ValueError, match="Self-referencing"):
            create_relation(
                db, sample_context.id, sample_context.id,
                relation_type="depends_on", created_by="admin_test",
            )


class TestListRelations:
    def test_list_by_context_id(self, db, sample_context):
        from app.models.context import ContextItem
        ctx2 = ContextItem(
            context_id="ctx_test_003",
            title="另一个上下文",
            content="另一个内容",
            content_hash="def456",
            domain="customer",
            lifecycle_status="active",
            created_by="test",
        )
        db.add(ctx2)
        db.commit()

        create_relation(db, sample_context.id, ctx2.id,
                        "depends_on", "admin_test")

        relations = list_relations(db, context_id=sample_context.id)
        assert len(relations) == 1

    def test_list_by_relation_type(self, db, sample_context):
        from app.models.context import ContextItem
        ctx2 = ContextItem(
            context_id="ctx_test_004",
            title="上下文四",
            content="内容四",
            content_hash="ghi789",
            domain="operations",
            lifecycle_status="active",
            created_by="test",
        )
        db.add(ctx2)
        db.commit()

        create_relation(db, sample_context.id, ctx2.id,
                        "depends_on", "admin_test")

        by_type = list_relations_by_type(db, "depends_on")
        assert len(by_type) >= 1
        assert by_type[0].relation_type == "depends_on"


class TestGetRelation:
    def test_get_existing(self, db, sample_context):
        from app.models.context import ContextItem
        ctx2 = ContextItem(
            context_id="ctx_test_005",
            title="上下文五",
            content="内容五",
            content_hash="jkl012",
            domain="operations",
            lifecycle_status="active",
            created_by="test",
        )
        db.add(ctx2)
        db.commit()

        rel = create_relation(db, sample_context.id, ctx2.id,
                              "depends_on", "admin_test")
        fetched = get_relation(db, rel.id)
        assert fetched is not None
        assert fetched.id == rel.id

    def test_get_nonexistent(self, db):
        assert get_relation(db, "00000000-0000-0000-0000-00000000dead") is None


class TestDeleteRelation:
    def test_delete_existing(self, db, sample_context):
        from app.models.context import ContextItem
        ctx2 = ContextItem(
            context_id="ctx_test_006",
            title="上下文六",
            content="内容六",
            content_hash="mno345",
            domain="operations",
            lifecycle_status="active",
            created_by="test",
        )
        db.add(ctx2)
        db.commit()

        rel = create_relation(db, sample_context.id, ctx2.id,
                              "depends_on", "admin_test")
        rel_id = rel.id  # Save id before deletion expires the object
        delete_relation(db, rel_id)
        assert get_relation(db, rel_id) is None

    def test_delete_nonexistent_raises(self, db):
        with pytest.raises(ValueError, match="not found"):
            delete_relation(db, "00000000-0000-0000-0000-00000000dead")
