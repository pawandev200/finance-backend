"""
FastAPI Dependencies
─────────────────────
This module is the bridge between HTTP layer and business logic.
All auth + permission checks flow through here using FastAPI's DI system.

Usage in endpoints:
    current_user: User = Depends(get_current_user)
    _: User = Depends(require_permission(Permission.TRANSACTION_CREATE))
"""

from functools import lru_cache
from typing import Callable

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.permissions import has_permission
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repo import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ── Current User Dependency ───────────────────────────────────────────────────

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Decodes the JWT, validates it, and returns the corresponding User.
    Raises 401 if the token is invalid or the user doesn't exist/is inactive.
    """
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        token_type: str = payload.get("token_type")

        if user_id is None or token_type != "access":
            raise UnauthorizedException()
    except JWTError:
        raise UnauthorizedException()

    user = UserRepository(db).get_by_id(user_id)
    if user is None:
        raise UnauthorizedException("User not found.")
    if not user.is_active:
        raise UnauthorizedException("Account is inactive.")

    return user


# ── Permission Guard Factory ──────────────────────────────────────────────────

def require_permission(permission: str) -> Callable:
    """
    Dependency factory that returns a FastAPI dependency
    which enforces a specific permission for the current user.

    Example:
        @router.post("/", dependencies=[Depends(require_permission(Permission.TRANSACTION_CREATE))])
    """
    def _check(current_user: User = Depends(get_current_user)) -> User:
        if not has_permission(current_user.role, permission):
            raise ForbiddenException(
                f"Your role '{current_user.role}' does not have '{permission}' permission."
            )
        return current_user

    return _check


# ── Request Context Helpers ───────────────────────────────────────────────────

def get_client_ip(request: Request) -> str:
    """Extracts real client IP, accounting for proxies."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_user_agent(request: Request) -> str:
    return request.headers.get("User-Agent", "unknown")
