"""
Role-Based Access Control (RBAC)
─────────────────────────────────
Design: Permission matrix approach instead of hardcoded role checks.
This makes adding new roles or permissions a config change, not a code change.

Role Hierarchy:
  VIEWER   → read-only dashboard access
  ANALYST  → viewer + analytics & trends
  ADMIN    → full system access
"""

from enum import Enum
from typing import Set


class Role(str, Enum):
    VIEWER = "viewer"
    ANALYST = "analyst"
    ADMIN = "admin"


# ── Permission Constants ──────────────────────────────────────────────────────

class Permission:
    # Transactions
    TRANSACTION_READ = "transactions:read"
    TRANSACTION_CREATE = "transactions:create"
    TRANSACTION_UPDATE = "transactions:update"
    TRANSACTION_DELETE = "transactions:delete"

    # Dashboard
    DASHBOARD_SUMMARY = "dashboard:summary"
    DASHBOARD_ANALYTICS = "dashboard:analytics"
    DASHBOARD_TRENDS = "dashboard:trends"

    # Users
    USER_READ = "users:read"
    USER_CREATE = "users:create"
    USER_UPDATE = "users:update"
    USER_DELETE = "users:delete"

    # Audit
    AUDIT_READ = "audit:read"


# ── Permission Matrix ─────────────────────────────────────────────────────────
# Extend this dict when adding new roles — no other code needs to change.

ROLE_PERMISSIONS: dict[Role, Set[str]] = {
    Role.VIEWER: {
        Permission.TRANSACTION_READ,
        Permission.DASHBOARD_SUMMARY,
    },
    Role.ANALYST: {
        Permission.TRANSACTION_READ,
        Permission.DASHBOARD_SUMMARY,
        Permission.DASHBOARD_ANALYTICS,
        Permission.DASHBOARD_TRENDS,
    },
    Role.ADMIN: {
        Permission.TRANSACTION_READ,
        Permission.TRANSACTION_CREATE,
        Permission.TRANSACTION_UPDATE,
        Permission.TRANSACTION_DELETE,
        Permission.DASHBOARD_SUMMARY,
        Permission.DASHBOARD_ANALYTICS,
        Permission.DASHBOARD_TRENDS,
        Permission.USER_READ,
        Permission.USER_CREATE,
        Permission.USER_UPDATE,
        Permission.USER_DELETE,
        Permission.AUDIT_READ,
    },
}


def has_permission(role: Role, permission: str) -> bool:
    """Check if a role has a specific permission."""
    return permission in ROLE_PERMISSIONS.get(role, set())
