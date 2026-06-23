"""Dialect-agnostic column types for the Context Platform.

When running with PostgreSQL: uses native pg types (UUID, ARRAY, JSONB, INET, Vector).
When running with SQLite (testing): falls back to SQLite-compatible types.

All models should import types from this module, not from sqlalchemy.dialects directly.
"""
from sqlalchemy import Column, String, Text, LargeBinary
from sqlalchemy.types import TypeDecorator

# ── UUID ───────────────────────────────────────────────────────────
# PostgreSQL: native UUID type. SQLite: stored as String(36).
try:
    from sqlalchemy.dialects.postgresql import UUID as _PG_UUID
    UUID = _PG_UUID
except ImportError:
    UUID = String(36)


# ── ARRAY ──────────────────────────────────────────────────────────
# PostgreSQL: native ARRAY. SQLite: stored as JSON string.
try:
    from sqlalchemy.dialects.postgresql import ARRAY as _PG_ARRAY
    import json

    class _SQLiteArray(TypeDecorator):
        """Store lists as JSON strings in SQLite."""
        impl = Text
        cache_ok = True

        def process_bind_param(self, value, dialect):
            if value is None:
                return None
            return json.dumps(value, ensure_ascii=False)

        def process_result_value(self, value, dialect):
            if value is None:
                return None
            return json.loads(value)

    ARRAY = _PG_ARRAY if _PG_UUID is not None else _SQLiteArray
except ImportError:
    ARRAY = _SQLiteArray() if '_SQLiteArray' in dir() else Text


# ── JSONB ──────────────────────────────────────────────────────────
# PostgreSQL: native JSONB. SQLite: stored as Text (JSON string).
try:
    from sqlalchemy.dialects.postgresql import JSONB as _PG_JSONB
    class _SQLiteJSONB(TypeDecorator):
        """Store JSON as text in SQLite."""
        impl = Text
        cache_ok = True

        def process_bind_param(self, value, dialect):
            if value is None or value == {}:
                return None
            import json
            return json.dumps(value, ensure_ascii=False)

        def process_result_value(self, value, dialect):
            if value is None:
                return {}
            import json
            return json.loads(value)

    JSONB = _PG_JSONB
except ImportError:
    JSONB = _SQLiteJSONB()


# ── INET ───────────────────────────────────────────────────────────
# PostgreSQL: native INET. SQLite: stored as String.
try:
    from sqlalchemy.dialects.postgresql import INET as _PG_INET
    INET = _PG_INET
except ImportError:
    INET = String(45)


# ── Vector (pgvector) ──────────────────────────────────────────────
# PostgreSQL: pgvector Vector. SQLite: LargeBinary.
try:
    from pgvector.sqlalchemy import Vector as _PGVector
    Vector = _PGVector
except ImportError:
    Vector = LargeBinary


# ── Re-exports ─────────────────────────────────────────────────────
__all__ = ["UUID", "ARRAY", "JSONB", "INET", "Vector"]
