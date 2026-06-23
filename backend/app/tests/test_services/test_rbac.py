"""Unit tests for the RBAC permission engine."""
import pytest
from app.core.rbac import (
    Operation, ROLE_HIERARCHY, check_permission,
    has_role_level, require_role, get_effective_filter,
)
from app.models.user import User


def make_user(role: str) -> User:
    """Helper to create a minimal User object for testing."""
    u = User()
    u.role = role
    u.id = "test-id"
    return u


class TestRoleHierarchy:
    def test_admin_highest(self):
        assert ROLE_HIERARCHY["admin"] == 4

    def test_consultant_lowest(self):
        assert ROLE_HIERARCHY["consultant"] == 1

    def test_admin_above_partner(self):
        assert ROLE_HIERARCHY["admin"] > ROLE_HIERARCHY["partner"]

    def test_partner_above_senior(self):
        assert ROLE_HIERARCHY["partner"] > ROLE_HIERARCHY["senior_consultant"]


class TestAdminPermissions:
    def test_admin_can_create_context(self):
        assert check_permission(make_user("admin"), Operation.CREATE_CONTEXT)

    def test_admin_can_delete_context(self):
        assert check_permission(make_user("admin"), Operation.DELETE_CONTEXT)

    def test_admin_can_manage_users(self):
        assert check_permission(make_user("admin"), Operation.MANAGE_USERS)

    def test_admin_can_manage_permissions(self):
        assert check_permission(make_user("admin"), Operation.MANAGE_PERMISSIONS)

    def test_admin_can_adjust_confidence(self):
        assert check_permission(make_user("admin"), Operation.ADJUST_CONFIDENCE)


class TestConsultantPermissions:
    def test_consultant_can_create_context(self):
        assert check_permission(make_user("consultant"), Operation.CREATE_CONTEXT)

    def test_consultant_cannot_delete_context(self):
        assert not check_permission(make_user("consultant"), Operation.DELETE_CONTEXT)

    def test_consultant_cannot_manage_users(self):
        assert not check_permission(make_user("consultant"), Operation.MANAGE_USERS)

    def test_consultant_can_submit_correction(self):
        assert check_permission(make_user("consultant"), Operation.SUBMIT_CORRECTION)

    def test_consultant_cannot_adjust_confidence(self):
        assert not check_permission(make_user("consultant"), Operation.ADJUST_CONFIDENCE)


class TestPartnerPermissions:
    def test_partner_can_verify_context(self):
        assert check_permission(make_user("partner"), Operation.VERIFY_CONTEXT)

    def test_partner_can_adjust_confidence(self):
        assert check_permission(make_user("partner"), Operation.ADJUST_CONFIDENCE)

    def test_partner_cannot_manage_users(self):
        assert not check_permission(make_user("partner"), Operation.MANAGE_USERS)

    def test_partner_can_export(self):
        assert check_permission(make_user("partner"), Operation.EXPORT_CONTEXT)

    def test_partner_can_view_metrics(self):
        assert check_permission(make_user("partner"), Operation.VIEW_METRICS)


class TestHasRoleLevel:
    def test_admin_has_consultant_level(self):
        assert has_role_level(make_user("admin"), "consultant")

    def test_consultant_does_not_have_admin_level(self):
        assert not has_role_level(make_user("consultant"), "admin")

    def test_same_role(self):
        assert has_role_level(make_user("partner"), "partner")

    def test_partner_above_senior(self):
        assert has_role_level(make_user("partner"), "senior_consultant")

    def test_require_role_same_as_has_role_level(self):
        assert require_role(make_user("admin"), "partner") == has_role_level(make_user("admin"), "partner")


class TestEffectiveFilter:
    def test_admin_sees_everything(self):
        assert get_effective_filter(make_user("admin")) is None

    def test_non_admin_has_filter(self):
        f = get_effective_filter(make_user("consultant"))
        assert f is not None
        assert f["role"] == "consultant"

    def test_partner_filter(self):
        f = get_effective_filter(make_user("partner"))
        assert f["role"] == "partner"
