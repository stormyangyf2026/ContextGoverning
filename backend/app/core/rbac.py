"""RBAC permission engine — Layer 1 of the three-layer permission model.

Role hierarchy (from most privileged to least):
    admin > partner > senior_consultant > consultant

Permission matrix: role × operation permissions.
"""
from enum import Enum
from typing import Optional

from app.models.user import User


class Operation(str, Enum):
    """CRUD + special operations on resources."""
    CREATE_CONTEXT = "create_context"
    UPDATE_CONTEXT = "update_context"
    DELETE_CONTEXT = "delete_context"
    VERIFY_CONTEXT = "verify_context"       # L2→L3 upgrade
    ADJUST_CONFIDENCE = "adjust_confidence"  # manual confidence override
    MANAGE_USERS = "manage_users"
    MANAGE_PERMISSIONS = "manage_permissions"
    MANAGE_CONFIG = "manage_config"
    VIEW_METRICS = "view_metrics"
    EXPORT_CONTEXT = "export_context"
    SUBMIT_CORRECTION = "submit_correction"
    RESOLVE_CONFLICT = "resolve_conflict"


# Role hierarchy numeric values (higher = more privileged)
ROLE_HIERARCHY = {
    "admin": 4,
    "partner": 3,
    "senior_consultant": 2,
    "consultant": 1,
}


# Role × Operation permission matrix
# True = allowed, False = denied
ROLE_PERMISSION_MATRIX: dict[str, set[Operation]] = {
    "admin": {
        Operation.CREATE_CONTEXT,
        Operation.UPDATE_CONTEXT,
        Operation.DELETE_CONTEXT,
        Operation.VERIFY_CONTEXT,
        Operation.ADJUST_CONFIDENCE,
        Operation.MANAGE_USERS,
        Operation.MANAGE_PERMISSIONS,
        Operation.MANAGE_CONFIG,
        Operation.VIEW_METRICS,
        Operation.EXPORT_CONTEXT,
        Operation.SUBMIT_CORRECTION,
        Operation.RESOLVE_CONFLICT,
    },
    "partner": {
        Operation.CREATE_CONTEXT,
        Operation.UPDATE_CONTEXT,
        Operation.VERIFY_CONTEXT,
        Operation.ADJUST_CONFIDENCE,
        Operation.VIEW_METRICS,
        Operation.EXPORT_CONTEXT,
        Operation.SUBMIT_CORRECTION,
        Operation.RESOLVE_CONFLICT,
    },
    "senior_consultant": {
        Operation.CREATE_CONTEXT,
        Operation.UPDATE_CONTEXT,
        Operation.VERIFY_CONTEXT,
        Operation.SUBMIT_CORRECTION,
        Operation.RESOLVE_CONFLICT,
    },
    "consultant": {
        Operation.CREATE_CONTEXT,
        Operation.SUBMIT_CORRECTION,
    },
}


def check_permission(user: User, operation: Operation) -> bool:
    """Check if user's role allows the given operation (Layer 1 RBAC)."""
    allowed = ROLE_PERMISSION_MATRIX.get(user.role, set())
    return operation in allowed


def has_role_level(user: User, minimum_role: str) -> bool:
    """Check if user's role is at least as high as the required minimum."""
    user_level = ROLE_HIERARCHY.get(user.role, 0)
    required_level = ROLE_HIERARCHY.get(minimum_role, 0)
    return user_level >= required_level


def require_role(user: User, minimum_role: str) -> bool:
    """Shortcut for has_role_level."""
    return has_role_level(user, minimum_role)


def get_effective_filter(user: User) -> Optional[dict]:
    """Get SQL-level filter conditions for the current user.

    Admin sees everything. Other roles see only what their role allows.
    Returns None (no filter) for admin, or a dict of filter conditions.
    """
    if user.role == "admin":
        return None  # No filtering
    return {"role": user.role}
