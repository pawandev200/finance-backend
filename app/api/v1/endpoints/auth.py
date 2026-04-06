"""
Auth Endpoints
──────────────

  POST /auth/register — Public self-registration
  POST /auth/login    — Exchange credentials for JWT tokens
  POST /auth/refresh  — Exchange refresh token for a new access token
  GET  /auth/me       — Return current user profile
  POST /auth/logout   — Client-side logout (stateless JWT)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HOW USER CREATION WORKS IN THIS SYSTEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Path 1 — Self-Registration (this file, /auth/register)
  ────────────────────────────────────────────────────────
  Open to the public. No token required.
  Role is ALWAYS forced to VIEWER, regardless of what the
  request body says. This prevents privilege escalation:
  nobody can give themselves ANALYST or ADMIN by self-registering.

  Path 2 — Admin-Created Users (/users/ POST, requires ADMIN token)
  ──────────────────────────────────────────────────────────────────
  An ADMIN can create users with any role (VIEWER, ANALYST, ADMIN).
  This is the only way to onboard team members who need elevated access.
  The first ADMIN always comes from the seed script (or a CLI bootstrap).
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, get_current_user, get_user_agent
from app.core.exceptions import UnauthorizedException
from app.core.permissions import Role
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.db.session import get_db
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.common import MessageResponse
from app.schemas.user import UserCreate, UserResponse
from app.services.audit_service import AuditService
from app.services.user_service import UserService
from jose import JWTError

router = APIRouter()


# ── Register ──────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=201,
    summary="Self-Register (Public)",
)
def register(
    data: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    **Public endpoint — no authentication required.**

    Anyone can register an account. The role is **always set to VIEWER**,
    regardless of what is sent in the request body.

    To get ANALYST or ADMIN access, an existing Admin must update your
    role via `PATCH /users/{id}`.

    This design prevents privilege escalation through self-registration —
    a core security requirement for any finance system.
    """
    service = UserService(db)

    # Security: ignore any role in the request body, always assign VIEWER
    create_data = UserCreate(
        email=data.email,
        full_name=data.full_name,
        password=data.password,
        role=Role.VIEWER,  # hardcoded — not from request
    )
    user = service.create_user(data=create_data)

    AuditService(db).log(
        user_id=user.id,
        action="REGISTER",
        resource="user",
        resource_id=user.id,
        new_value={"email": user.email, "role": user.role},
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )

    return user


# ── Login ─────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse, summary="User Login")
def login(
    credentials: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Authenticates user credentials and returns access + refresh tokens.

    - **Access token**: short-lived (30 min), sent in Authorization: Bearer header
    - **Refresh token**: long-lived (7 days), used only to get a new access token
    """
    service = UserService(db)
    user = service.authenticate(email=credentials.email, password=credentials.password)

    if not user:
        # Deliberately vague — do not reveal whether the email exists
        raise UnauthorizedException("Invalid email or password.")

    access_token = create_access_token(data={"sub": user.id})
    refresh_token = create_refresh_token(data={"sub": user.id})

    AuditService(db).log(
        user_id=user.id,
        action="LOGIN",
        resource="auth",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


# ── Refresh Token ─────────────────────────────────────────────────────────────

@router.post("/refresh", response_model=AccessTokenResponse, summary="Refresh Access Token")
def refresh_token(body: RefreshRequest, db: Session = Depends(get_db)):
    """
    Accepts a valid refresh token and issues a new short-lived access token.
    Returns 401 if the refresh token is expired or invalid.
    """
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("token_type") != "refresh":
            raise UnauthorizedException("Invalid token type.")
        user_id: str = payload.get("sub")
    except JWTError:
        raise UnauthorizedException("Refresh token is invalid or expired.")

    from app.repositories.user_repo import UserRepository
    user = UserRepository(db).get_by_id(user_id)
    if not user or not user.is_active:
        raise UnauthorizedException()

    return AccessTokenResponse(
        access_token=create_access_token(data={"sub": user.id})
    )


# ── Me ────────────────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserResponse, summary="Get Current User")
def get_me(current_user=Depends(get_current_user)):
    """Returns the profile of the currently authenticated user."""
    return current_user


# ── Logout ────────────────────────────────────────────────────────────────────

@router.post("/logout", response_model=MessageResponse, summary="Logout")
def logout(
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Stateless JWT logout — instructs the client to discard its tokens.
    Production: add token to a Redis blocklist for true server-side invalidation.
    """
    AuditService(db).log(
        user_id=current_user.id,
        action="LOGOUT",
        resource="auth",
        ip_address=get_client_ip(request),
    )
    return MessageResponse(message="Logged out successfully.")
