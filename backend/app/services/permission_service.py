"""Three-layer permission service (Layer 2: Entity Boundary + Layer 3: Sensitivity).

Layers:
    1. RBAC (app/core/rbac.py) — role × operation matrix
    2. Entity Boundary (this file) — user's assigned entities
    3. Sensitivity (this file) — visibility level check

Final permission = Layer1 AND Layer2 AND Layer3 (most restrictive wins).
"""
from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User, UserEntityAssignment
from app.models.permission import Permission
from app.models.context import ContextItem
from app.models.context_entity import ContextEntityMap

# Sensitivity × Role access matrix
# True = role can access this sensitivity level
SENSITIVITY_MATRIX = {
    "public": {"admin": True, "partner": True, "senior_consultant": True, "consultant": True},
    "internal": {"admin": True, "partner": True, "senior_consultant": True, "consultant": True},
    "confidential": {"admin": True, "partner": True, "senior_consultant": True, "consultant": False},
    "top_secret": {"admin": True, "partner": True, "senior_consultant": False, "consultant": False},
}


def check_entity_boundary(
    db: Session, user: User, context_id: str
) -> tuple[bool, str]:
    """Layer 2: Check if user has entity assignment allowing access to this context.

    Returns (has_access, reason).
    """
    # Admin bypasses entity boundary checks
    if user.role == "admin":
        return True, "admin_bypass"

    # Get entities linked to this context
    entity_links = (
        db.query(ContextEntityMap)
        .filter(ContextEntityMap.context_id == context_id)
        .all()
    )

    if not entity_links:
        # Context with no entity restrictions — allow by default
        return True, "no_entity_restriction"

    entity_ids = [link.entity_id for link in entity_links]

    # Check if user has assignment to any of these entities
    assignments = (
        db.query(UserEntityAssignment)
        .filter(
            UserEntityAssignment.user_id == user.id,
            UserEntityAssignment.entity_id.in_(entity_ids),
        )
        .all()
    )

    if not assignments:
        return False, "entity_boundary_denied"

    return True, "entity_boundary_granted"


def check_sensitivity(
    db: Session, user: User, context: ContextItem
) -> tuple[bool, str]:
    """Layer 3: Check if user's role allows viewing this context's sensitivity level.

    Returns (has_access, reason).
    """
    permission = (
        db.query(Permission)
        .filter(Permission.context_id == context.id)
        .first()
    )

    if permission is None:
        # Default: internal visibility
        visibility = "internal"
        allowed_roles = []
    else:
        visibility = permission.visibility
        allowed_roles = permission.allowed_roles or []

    # Check allowed_roles first (if specified, they override the sensitivity matrix)
    if allowed_roles:
        if user.role in allowed_roles:
            return True, "explicit_role_allowed"
        return False, f"role_not_in_allowed_roles:{user.role}"

    # Fall back to sensitivity matrix
    role_access = SENSITIVITY_MATRIX.get(visibility, {}).get(user.role, False)
    if role_access:
        return True, f"sensitivity_granted:{visibility}"
    return False, f"sensitivity_denied:{visibility}"


def check_full_permission(
    db: Session, user: User, context_id: str, rbac_operation: Optional[str] = None
) -> tuple[bool, str]:
    """Combined three-layer permission check.

    Args:
        db: Database session
        user: Current user
        context_id: Context to check access for
        rbac_operation: Optional RBAC operation to check (Layer 1)

    Returns (has_access, reason).
    """
    # Layer 1: RBAC (only if operation specified)
    if rbac_operation:
        from app.core.rbac import check_permission, Operation
        try:
            op = Operation(rbac_operation)
        except ValueError:
            return False, f"unknown_operation:{rbac_operation}"
        if not check_permission(user, op):
            return False, f"rbac_denied:{rbac_operation}"

    # Layer 2: Entity Boundary
    entity_access, entity_reason = check_entity_boundary(db, user, context_id)
    if not entity_access:
        return False, entity_reason

    # Layer 3: Sensitivity
    context = db.query(ContextItem).filter(ContextItem.id == context_id).first()
    if context is None:
        return False, "context_not_found"

    sensitivity_access, sensitivity_reason = check_sensitivity(db, user, context)
    if not sensitivity_access:
        return False, sensitivity_reason

    return True, "full_permission_granted"


def get_effective_filters(db: Session, user: User) -> dict:
    """Generate SQL-level pre-filters for the current user.

    Used to apply permission filtering at the query level (Design Doc §3.7.7).
    Returns a dict of filter conditions to merge into SQLAlchemy queries.

    For admin: returns empty filter (sees everything).
    For others: returns entity-boundary and sensitivity filters.
    """
    if user.role == "admin":
        return {}

    filters = {}

    # Entity boundary filter
    assignments = (
        db.query(UserEntityAssignment.entity_id)
        .filter(UserEntityAssignment.user_id == user.id)
        .all()
    )
    if assignments:
        entity_ids = [a.entity_id for a in assignments]
        filters["entity_ids"] = entity_ids

    # Sensitivity filter
    sensitivities = [
        s for s, roles in SENSITIVITY_MATRIX.items() if roles.get(user.role, False)
    ]
    if sensitivities:
        filters["allowed_sensitivities"] = sensitivities

    return filters
