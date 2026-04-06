"""
User Service
─────────────
All user-related business logic lives here.
The service layer is the only place that knows about both
the repository (data) and the domain rules (logic).
"""

from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException
from app.core.permissions import Role
from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.user import UserCreate, UserUpdate
from app.services.audit_service import AuditService


class UserService:
    def __init__(self, db: Session):
        self.repo = UserRepository(db)
        self.audit = AuditService(db)

    def create_user(
        self,
        data: UserCreate,
        created_by_id: Optional[str] = None,
    ) -> User:
        if self.repo.email_exists(data.email):
            raise ConflictException(f"A user with email '{data.email}' already exists.")

        user = User(
            email=data.email,
            full_name=data.full_name,
            hashed_password=get_password_hash(data.password),
            role=data.role,
        )
        user = self.repo.create(user)

        self.audit.log(
            user_id=created_by_id or user.id,
            action="CREATE",
            resource="user",
            resource_id=user.id,
            new_value={"email": user.email, "role": user.role},
        )
        return user

    def get_user(self, user_id: str) -> User:
        user = self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("User", user_id)
        return user

    def get_all_users(
        self, skip: int = 0, limit: int = 20
    ) -> Tuple[List[User], int]:
        return self.repo.get_all_paginated(skip=skip, limit=limit)

    def update_user(
        self,
        user_id: str,
        data: UserUpdate,
        updated_by_id: str,
    ) -> User:
        user = self.get_user(user_id)
        old_snapshot = {"role": user.role, "is_active": user.is_active, "full_name": user.full_name}

        if data.full_name is not None:
            user.full_name = data.full_name
        if data.role is not None:
            user.role = data.role
        if data.is_active is not None:
            user.is_active = data.is_active

        user = self.repo.save(user)

        self.audit.log(
            user_id=updated_by_id,
            action="UPDATE",
            resource="user",
            resource_id=user.id,
            old_value=old_snapshot,
            new_value={"role": user.role, "is_active": user.is_active, "full_name": user.full_name},
        )
        return user

    def authenticate(self, email: str, password: str) -> Optional[User]:
        """Returns User if credentials are valid, None otherwise."""
        user = self.repo.get_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            return None
        return user
