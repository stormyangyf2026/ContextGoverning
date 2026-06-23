"""Unit tests for entity service."""
import pytest
from app.services.entity_service import (
    create_entity, get_entity, list_entities, update_entity,
)


class TestCreateEntity:
    def test_create_basic_entity(self, db):
        entity = create_entity(db, "测试实体", "project", domain="operations")
        assert entity.name == "测试实体"
        assert entity.type == "project"
        assert entity.domain == "operations"

    def test_create_entity_with_aliases(self, db):
        entity = create_entity(db, "公司A", "customer", aliases=["A公司", "CompanyA"])
        assert "A公司" in entity.aliases

    def test_create_entity_with_metadata(self, db):
        entity = create_entity(db, "公司B", "customer", metadata={"industry": "tech"})
        assert entity.extra_data.get("industry") == "tech"

    def test_create_duplicate_entity_returns_existing(self, db):
        """Idempotent: same name + type returns existing entity."""
        e1 = create_entity(db, "重复实体", "project")
        e2 = create_entity(db, "重复实体", "project")
        assert e1.id == e2.id

    def test_same_name_different_type_creates_new(self, db):
        e1 = create_entity(db, "实体X", "project")
        e2 = create_entity(db, "实体X", "customer")
        assert e1.id != e2.id


class TestGetEntity:
    def test_get_existing_entity(self, db, sample_entity):
        entity = get_entity(db, sample_entity.id)
        assert entity is not None
        assert entity.name == sample_entity.name

    def test_get_nonexistent_entity(self, db):
        entity = get_entity(db, "00000000-0000-0000-0000-00000000dead")
        assert entity is None


class TestListEntities:
    def test_list_all(self, db, sample_entity):
        entities = list_entities(db)
        assert len(entities) >= 1

    def test_list_by_type(self, db):
        create_entity(db, "公司C", "customer")
        create_entity(db, "项目D", "project")
        customers = list_entities(db, entity_type="customer")
        assert all(e.type == "customer" for e in customers)

    def test_list_by_domain(self, db):
        create_entity(db, "公司E", "customer", domain="customer")
        create_entity(db, "公司F", "customer", domain="operations")
        result = list_entities(db, domain="customer")
        assert all(e.domain == "customer" for e in result)

    def test_list_with_search(self, db):
        create_entity(db, "深空科技", "customer")
        create_entity(db, "远洋集团", "customer")
        result = list_entities(db, search="深空")
        assert len(result) == 1
        assert result[0].name == "深空科技"


class TestUpdateEntity:
    def test_update_name(self, db, sample_entity):
        updated = update_entity(db, sample_entity.id, name="新名称")
        assert updated.name == "新名称"

    def test_update_domain(self, db, sample_entity):
        updated = update_entity(db, sample_entity.id, domain="operations")
        assert updated.domain == "operations"

    def test_update_aliases(self, db, sample_entity):
        updated = update_entity(db, sample_entity.id, aliases=["别名1", "别名2"])
        assert len(updated.aliases) == 2

    def test_update_nonexistent_raises(self, db):
        with pytest.raises(ValueError, match="not found"):
            update_entity(db, "00000000-0000-0000-0000-00000000dead", name="x")
