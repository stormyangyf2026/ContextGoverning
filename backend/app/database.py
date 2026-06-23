"""SQLAlchemy engine and session configuration.

Engine is created lazily (on first use) so that tests can override
DATABASE_URL via environment variable before the engine is built.

Usage:
    from app.database import get_engine, get_session_factory, get_db
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config import get_settings

_engine = None
_SessionLocal = None


def get_engine():
    """Lazily create and return the SQLAlchemy engine.

    On first call, reads DATABASE_URL from Settings and builds the engine.
    SQLite URLs skip pool parameters automatically.
    Subsequent calls return the cached engine.
    """
    global _engine, _SessionLocal
    if _engine is not None:
        return _engine

    settings = get_settings()
    url = settings.database_url

    kwargs = {"echo": (settings.log_level == "DEBUG")}

    # PostgreSQL: use connection pooling parameters
    # SQLite: skip pool params (uses SingletonThreadPool); set check_same_thread
    if "sqlite" not in url:
        kwargs.update({
            "pool_size": settings.db_pool_size,
            "max_overflow": settings.db_max_overflow,
            "pool_pre_ping": settings.db_pool_pre_ping,
            "pool_recycle": settings.db_pool_recycle,
        })
    else:
        kwargs["connect_args"] = {"check_same_thread": False}

    _engine = create_engine(url, **kwargs)
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine


def get_session_factory():
    """Return the session factory (lazy — triggers engine creation if needed)."""
    get_engine()  # ensure engine exists
    return _SessionLocal


def get_db() -> Session:
    """FastAPI dependency: yields a database session."""
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()
