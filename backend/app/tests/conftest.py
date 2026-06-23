"""Shared test fixtures for the Context Platform.

Strategy:
    - Sets DATABASE_URL to PostgreSQL test database BEFORE any app imports
    - Uses the app's own lazy get_engine() for consistency
    - Creates and drops tables within a transaction per test for isolation
    - Includes comprehensive mock factories for all models
"""
import os
import uuid

# ── MUST be set BEFORE any app imports that trigger engine creation ──
os.environ["DATABASE_URL"] = "postgresql://postgres:123456@localhost:5432/context_platform_test"
os.environ["JWT_SECRET_KEY"] = "jwt-test-secret-key-32chars!!"
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["RATE_LIMIT_DEFAULT"] = "600 per minute"

import pytest
import hashlib
from datetime import date, datetime, timezone, timedelta
from typing import Generator, Optional, List, Dict, Any

from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models.base import Base
from app.database import get_engine, get_session_factory, get_db
from app.main import app
from app.core.security import create_access_token, hash_password
from app.models.user import User
from app.models.context import ContextItem
from app.models.entity import Entity
from app.models.relation import Relation
from app.models.context_entity import ContextEntityMap
from app.models.workspace import Workspace
from app.models.api_key import ApiKey
from app.models.audit import AuditLog


# ── Database fixtures ──────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create all tables once per test session.

    Tables are dropped in reverse dependency order to avoid
    'DependentObjectsStillExist' errors from PostgreSQL foreign keys.
    """
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    yield
    # Drop tables with CASCADE to handle FK dependencies cleanly.
    # This is safe in a test database because each test uses a transaction
    # that is rolled back, so the tables are empty at teardown time.
    # We use raw CASCADE to avoid ordering issues with new tables that
    # reference existing ones (e.g. review_records → workspaces).
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("DROP SCHEMA public CASCADE")
            conn.exec_driver_sql("CREATE SCHEMA public")
            conn.commit()
    except Exception:
        # Final fallback: try standard drop_all
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(setup_database) -> Generator[Session, None, None]:
    """Provide a transaction-rolled-back session per test."""
    factory = get_session_factory()
    connection = get_engine().connect()
    transaction = connection.begin()
    session = factory(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def db(db_session: Session) -> Session:
    """Shorter alias for db_session."""
    return db_session


# ── FastAPI TestClient ─────────────────────────────────────────────

@pytest.fixture
def client(db_session: Session) -> TestClient:
    """TestClient with database session override."""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Test Users ─────────────────────────────────────────────────────

@pytest.fixture
def admin_user(db_session: Session) -> User:
    user = User(
        id="00000000-0000-0000-0000-000000000001",
        username="admin_test",
        email="admin@test.com",
        role="admin",
        display_name="Test Admin",
        hashed_password=hash_password("admin123"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def consultant_user(db_session: Session) -> User:
    user = User(
        id="00000000-0000-0000-0000-000000000002",
        username="consultant_test",
        email="consultant@test.com",
        role="consultant",
        display_name="Test Consultant",
        hashed_password=hash_password("consultant123"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def partner_user(db_session: Session) -> User:
    user = User(
        id="00000000-0000-0000-0000-000000000003",
        username="partner_test",
        email="partner@test.com",
        role="partner",
        display_name="Test Partner",
        hashed_password=hash_password("partner123"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ── Auth Tokens ────────────────────────────────────────────────────

@pytest.fixture
def admin_token(admin_user: User) -> str:
    return create_access_token({"sub": admin_user.id, "role": admin_user.role})


@pytest.fixture
def consultant_token(consultant_user: User) -> str:
    return create_access_token({"sub": consultant_user.id, "role": consultant_user.role})


@pytest.fixture
def partner_token(partner_user: User) -> str:
    return create_access_token({"sub": partner_user.id, "role": partner_user.role})


@pytest.fixture
def auth_headers(admin_token: str) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def consultant_auth_headers(consultant_token: str) -> dict:
    return {"Authorization": f"Bearer {consultant_token}"}


@pytest.fixture
def partner_auth_headers(partner_token: str) -> dict:
    return {"Authorization": f"Bearer {partner_token}"}


# ── Test Data Helpers ──────────────────────────────────────────────

@pytest.fixture
def sample_context(db_session: Session) -> ContextItem:
    content = "这是一个测试上下文的内容"
    ctx = ContextItem(
        context_id="ctx_test_001",
        title="测试上下文",
        content=content,
        content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        domain="operations",
        confidence_level="L2",
        confidence_score=0.65,
        confidence_source_type="manual_entry",
        lifecycle_status="active",
        created_by="admin_test",
        version=1,
        is_immutable=False,
    )
    db_session.add(ctx)
    db_session.commit()
    db_session.refresh(ctx)
    return ctx


@pytest.fixture
def sample_entity(db_session: Session) -> Entity:
    entity = Entity(
        name="测试公司",
        type="customer",
        domain="customer",
    )
    db_session.add(entity)
    db_session.commit()
    db_session.refresh(entity)
    return entity


# ── Mock Factories ─────────────────────────────────────────────────

def make_context(
    db: Session,
    context_id: Optional[str] = None,
    title: str = "Test Context",
    content: str = "Test content for search testing",
    domain: str = "operations",
    confidence_level: str = "L2",
    confidence_score: float = 0.65,
    confidence_source_type: str = "manual_entry",
    lifecycle_status: str = "active",
    created_by: str = "admin_test",
    **kwargs,
) -> ContextItem:
    """Factory to create a ContextItem with sensible defaults."""
    cid = context_id or f"ctx_{uuid.uuid4().hex[:12]}"
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    ctx = ContextItem(
        context_id=cid,
        title=title,
        content=content,
        content_hash=content_hash,
        domain=domain,
        confidence_level=confidence_level,
        confidence_score=confidence_score,
        confidence_source_type=confidence_source_type,
        lifecycle_status=lifecycle_status,
        created_by=created_by,
        version=kwargs.pop("version", 1),
        is_immutable=kwargs.pop("is_immutable", False),
        **kwargs,
    )
    db.add(ctx)
    db.commit()
    db.refresh(ctx)
    return ctx


def make_entity(
    db: Session,
    name: str = "Test Entity",
    type: str = "customer",
    domain: str = "customer",
    **kwargs,
) -> Entity:
    """Factory to create an Entity with sensible defaults."""
    entity = Entity(
        name=name,
        type=type,
        domain=domain,
        **kwargs,
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity


def make_relation(
    db: Session,
    source_id,
    target_id,
    relation_type: str = "depends_on",
    direction: str = "forward",
    **kwargs,
) -> Relation:
    """Factory to create a Relation."""
    created_by = kwargs.pop("created_by", "test_user")
    rel = Relation(
        source_id=source_id,
        target_id=target_id,
        relation_type=relation_type,
        direction=direction,
        created_by=created_by,
        **kwargs,
    )
    db.add(rel)
    db.commit()
    db.refresh(rel)
    return rel


def make_workspace(
    db: Session,
    name: str = "Test Workspace",
    slug: Optional[str] = None,
    **kwargs,
) -> Workspace:
    """Factory to create a Workspace."""
    ws_slug = slug or f"ws_{uuid.uuid4().hex[:8]}"
    ws = Workspace(
        name=name,
        slug=ws_slug,
        workspace_id=f"workspace_{ws_slug}",
        **kwargs,
    )
    db.add(ws)
    db.commit()
    db.refresh(ws)
    return ws


def make_context_entity_map(
    db: Session,
    context_id,
    entity_id,
    **kwargs,
) -> ContextEntityMap:
    """Factory to create a ContextEntityMap."""
    mapping = ContextEntityMap(
        context_id=context_id,
        entity_id=entity_id,
        **kwargs,
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping


# ── Rich test data fixtures ────────────────────────────────────────

@pytest.fixture
def sample_contexts(db_session: Session) -> List[ContextItem]:
    """Create multiple sample contexts for search/graph testing."""
    contexts = []
    for i in range(5):
        content = f"测试内容 {i}: 公司营收增长 {i*10}%"
        ctx = ContextItem(
            context_id=f"ctx_search_00{i}",
            title=f"测试上下文 {i}",
            content=content,
            content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
            domain="operations" if i % 2 == 0 else "customer",
            confidence_level=f"L{min(i+1, 5)}",
            confidence_score=0.5 + i * 0.1,
            confidence_source_type="api_import" if i % 2 == 0 else "feishu_doc",
            lifecycle_status="active" if i != 4 else "contradicted",
            created_by="admin_test",
            version=1,
            is_immutable=(i == 0),
        )
        db_session.add(ctx)
        contexts.append(ctx)
    db_session.commit()
    for ctx in contexts:
        db_session.refresh(ctx)
    return contexts


@pytest.fixture
def sample_entities(db_session: Session) -> List[Entity]:
    """Create multiple sample entities for graph testing."""
    entities = []
    for name, etype, edomain in [
        ("公司A", "customer", "customer"),
        ("公司B", "supplier", "operations"),
        ("产品X", "product", "customer"),
        ("项目Y", "project", "project"),
    ]:
        entity = Entity(name=name, type=etype, domain=edomain)
        db_session.add(entity)
        entities.append(entity)
    db_session.commit()
    for e in entities:
        db_session.refresh(e)
    return entities


@pytest.fixture
def sample_relations(db_session: Session, sample_contexts, sample_entities) -> List[Relation]:
    """Create sample relations between contexts and entities."""
    rels = []
    for i in range(min(3, len(sample_contexts))):
        rel = Relation(
            source_id=sample_contexts[i].id,
            target_id=sample_contexts[(i+1) % len(sample_contexts)].id,
            relation_type="depends_on" if i % 2 == 0 else "informs",
            direction="forward",
        )
        db_session.add(rel)
        rels.append(rel)
    db_session.commit()
    for r in rels:
        db_session.refresh(r)
    return rels


@pytest.fixture
def sample_workspace(db_session: Session) -> Workspace:
    return make_workspace(db_session, name="Default Workspace", slug="default")


@pytest.fixture
def sample_api_key(db_session: Session, sample_workspace) -> ApiKey:
    key = ApiKey(
        workspace_id=sample_workspace.id,
        key_hash="test_api_key_hash_value_32chars",
        key_prefix="cp_tst",
        name="Test API Key",
        is_active=True,
    )
    db_session.add(key)
    db_session.commit()
    db_session.refresh(key)
    return key
