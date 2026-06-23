"""Unit tests for permission service (Layer 2: Entity Boundary + Layer 3: Sensitivity)."""
import pytest
from app.services.permission_service import (
    SENSITIVITY_MATRIX, check_full_permission, get_effective_filters,
)
from app.models.user import User, UserEntityAssignment
from app.models.permission import Permission as PermissionModel


def make_user(role: str, user_id: str = "test-user-id") -> User:
    """Helper: create minimal User for permission checks."""
    u = User()
    u.id = user_id
    u.role = role
    u.is_active = True
    return u


class TestSensitivityMatrix:
    def test_admin_sees_all_levels(self):
        """Admin can access all 4 sensitivity levels."""
        for vis in ("public", "internal", "confidential", "top_secret"):
            assert SENSITIVITY_MATRIX[vis]["admin"] is True

    def test_consultant_limited(self):
        assert SENSITIVITY_MATRIX["public"]["consultant"] is True
        assert SENSITIVITY_MATRIX["internal"]["consultant"] is True
        assert SENSITIVITY_MATRIX["confidential"]["consultant"] is False
        assert SENSITIVITY_MATRIX["top_secret"]["consultant"] is False

    def test_partner_sees_up_to_top_secret(self):
        assert SENSITIVITY_MATRIX["top_secret"]["partner"] is True

    def test_senior_consultant_sees_up_to_confidential(self):
        assert SENSITIVITY_MATRIX["confidential"]["senior_consultant"] is True
        assert SENSITIVITY_MATRIX["top_secret"]["senior_consultant"] is False


class TestEffectiveFilters:
    def test_admin_gets_empty_filter(self, db):
        """Admin should have no pre-filter (sees everything)."""
        user = make_user("admin")
        filters = get_effective_filters(db, user)
        assert filters == {}
