"""
User Management Endpoints
──────────────────────────
All routes require ADMIN role except GET /users/me (handled in auth).

POST   /users          → Create user (ADMIN)
GET    /users          → List all users (ADMIN)
GET    /users/{id}     → Get user by ID (ADMIN)
PATCH  /users/{id}     → Update user role/status (ADMIN)
GET    /users/audit-logs → View audit trail (ADMIN)
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.permissions import Permission
from app.db.session import get_db
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.audit_service import AuditService
from app.services.user_service import UserService

router = APIRouter()

# Convenience alias — all routes here require ADMIN
AdminRequired = Depends(require_permission(Permission.USER_READ))


@router.post(
    "/",
    response_model=UserResponse,
    status_code=201,
    summary="Create User",
    dependencies=[Depends(require_permission(Permission.USER_CREATE))],
)
def create_user(
    data: UserCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Creates a new user. Only ADMIN can assign roles."""
    service = UserService(db)
    return service.create_user(data=data, created_by_id=current_user.id)


@router.get(
    "/",
    response_model=PaginatedResponse[UserResponse],
    summary="List Users",
    dependencies=[Depends(require_permission(Permission.USER_READ))],
)
def list_users(
    page: int = Query(default=1, ge=1, description="Page number"),
    size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    """Returns a paginated list of all users."""
    import math
    service = UserService(db)
    skip = (page - 1) * size
    users, total = service.get_all_users(skip=skip, limit=size)
    return PaginatedResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if total else 1,
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get User by ID",
    dependencies=[Depends(require_permission(Permission.USER_READ))],
)
def get_user(user_id: str, db: Session = Depends(get_db)):
    """Returns a specific user's details."""
    service = UserService(db)
    return service.get_user(user_id)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update User",
    dependencies=[Depends(require_permission(Permission.USER_UPDATE))],
)
def update_user(
    user_id: str,
    data: UserUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Updates user role, status, or name. Only ADMIN can change roles."""
    service = UserService(db)
    return service.update_user(user_id=user_id, data=data, updated_by_id=current_user.id)


@router.get(
    "/{user_id}/audit-logs",
    summary="Get User Audit Logs",
    dependencies=[Depends(require_permission(Permission.AUDIT_READ))],
)
def get_user_audit_logs(
    user_id: str,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Returns audit trail for a specific user. ADMIN only."""
    import math
    skip = (page - 1) * size
    service = AuditService(db)
    logs, total = service.get_logs(user_id=user_id, skip=skip, limit=size)
    return {
        "items": [
            {
                "id": log.id,
                "action": log.action,
                "resource": log.resource,
                "resource_id": log.resource_id,
                "ip_address": log.ip_address,
                "created_at": log.created_at,
            }
            for log in logs
        ],
        "total": total,
        "page": page,
        "size": size,
        "pages": math.ceil(total / size) if total else 1,
    }
