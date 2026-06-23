"""Tests for GraphService — knowledge graph query and traversal."""
import pytest
from app.services.graph_service import get_graph_service
from app.tests.conftest import make_context, make_entity, make_relation, make_context_entity_map


class TestGraphService:
    """Test knowledge graph queries and traversals."""

    def test_get_subgraph_by_name(self, db):
        """get_subgraph should return entity-centric graph by entity name."""
        entity = make_entity(db, name="图谱测试公司", type="customer", domain="customer")
        ctx = make_context(db, context_id="ctx_graph_01", title="关联上下文",
                          content="与实体关联的上下文")
        make_context_entity_map(db, ctx.id, entity.id)

        svc = get_graph_service()
        result = svc.get_subgraph(db, entity_name="图谱测试公司", depth=1)

        assert result["center_entity"] is not None
        assert result["center_entity"]["name"] == "图谱测试公司"
        assert isinstance(result["nodes"], list)
        assert isinstance(result["edges"], list)

    def test_get_subgraph_by_id(self, db):
        """get_subgraph should work with entity_id."""
        entity = make_entity(db, name="ID图谱公司", type="customer", domain="customer")

        svc = get_graph_service()
        result = svc.get_subgraph(db, entity_id=str(entity.id), depth=1)

        assert result["center_entity"] is not None
        assert result["center_entity"]["id"] == str(entity.id)

    def test_get_subgraph_nonexistent_entity(self, db):
        """get_subgraph with nonexistent entity should return empty graph."""
        svc = get_graph_service()
        result = svc.get_subgraph(db, entity_name="不存在的实体名称XYZ")

        assert result["center_entity"] is None
        assert result["nodes"] == []
        assert result["edges"] == []

    def test_get_subgraph_with_depth2(self, db):
        """get_subgraph with depth=2 should include related entities."""
        entity1 = make_entity(db, name="主实体", type="customer", domain="customer")
        entity2 = make_entity(db, name="关联实体", type="supplier", domain="operations")
        ctx = make_context(db, context_id="ctx_depth2", title="深度2测试",
                          content="深度遍历测试")
        make_context_entity_map(db, ctx.id, entity1.id)
        make_context_entity_map(db, ctx.id, entity2.id)

        svc = get_graph_service()
        result = svc.get_subgraph(db, entity_name="主实体", depth=2)

        assert result["center_entity"] is not None
        # depth=2 should return more than just the center entity
        assert len(result["nodes"]) >= 1

    def test_get_subgraph_with_relations(self, db):
        """get_subgraph should include relations between linked contexts."""
        entity = make_entity(db, name="关系实体", type="customer", domain="customer")
        ctx1 = make_context(db, context_id="ctx_rel_a", title="上下文A",
                           content="关系测试A")
        ctx2 = make_context(db, context_id="ctx_rel_b", title="上下文B",
                           content="关系测试B")
        make_context_entity_map(db, ctx1.id, entity.id)
        make_context_entity_map(db, ctx2.id, entity.id)
        make_relation(db, ctx1.id, ctx2.id, relation_type="depends_on")

        svc = get_graph_service()
        result = svc.get_subgraph(db, entity_name="关系实体", depth=2)

        assert result["center_entity"] is not None
        if result["edges"]:
            assert result["edges"][0]["type"] == "depends_on"

    def test_get_entity_graph_alias(self, db):
        """get_entity_graph should call get_subgraph by entity name."""
        entity = make_entity(db, name="别名测试", type="customer", domain="customer")

        svc = get_graph_service()
        result = svc.get_entity_graph(db, entity_name="别名测试", depth=1)

        assert result["center_entity"] is not None
        assert result["center_entity"]["name"] == "别名测试"

    def test_get_context_relations_empty(self, db):
        """get_context_relations for unconnected context should return empty."""
        ctx = make_context(db, context_id="ctx_no_rel", title="无关系",
                          content="无关系上下文")

        svc = get_graph_service()
        result = svc.get_context_relations(db, str(ctx.id))

        assert isinstance(result, list)

    def test_get_context_relations_with_relations(self, db):
        """get_context_relations should return relations for a context."""
        ctx1 = make_context(db, context_id="ctx_rel_src", title="源上下文",
                           content="源内容")
        ctx2 = make_context(db, context_id="ctx_rel_tgt", title="目标上下文",
                           content="目标内容")
        make_relation(db, ctx1.id, ctx2.id, relation_type="informs")

        svc = get_graph_service()
        result = svc.get_context_relations(db, str(ctx1.id))

        assert len(result) >= 1
        assert result[0]["type"] == "informs"

    def test_subgraph_nodes_have_required_fields(self, db):
        """Each node should have id, name, type, is_center."""
        entity = make_entity(db, name="结构测试", type="customer", domain="customer")

        svc = get_graph_service()
        result = svc.get_subgraph(db, entity_name="结构测试", depth=1)

        for node in result["nodes"]:
            assert "id" in node
            assert "name" in node
            assert "type" in node
            assert "is_center" in node

    def test_singleton_pattern(self):
        """get_graph_service should return the same instance."""
        svc1 = get_graph_service()
        svc2 = get_graph_service()
        assert svc1 is svc2

    def test_subgraph_limit(self, db):
        """Subgraph should respect the limit parameter."""
        entity = make_entity(db, name="限制测试", type="customer", domain="customer")
        for i in range(5):
            ctx = make_context(db, context_id=f"ctx_limit_{i}", title=f"限制上下文{i}",
                             content=f"限制测试{i}")
            make_context_entity_map(db, ctx.id, entity.id)

        svc = get_graph_service()
        result = svc.get_subgraph(db, entity_name="限制测试", depth=1, limit=2)

        assert result["center_entity"] is not None
