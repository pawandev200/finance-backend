"""
Generic Base Repository
───────────────────────
Implements common CRUD operations as a reusable generic class.
Concrete repositories extend this and add domain-specific queries.

Design choice: Repository pattern decouples the service layer
from SQLAlchemy specifics — services never import Session directly.
"""

from typing import Generic, List, Optional, Type, TypeVar

from sqlalchemy.orm import Session

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db

    def get_by_id(self, id: str) -> Optional[ModelType]:
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def count(self) -> int:
        return self.db.query(self.model).count()

    def create(self, obj: ModelType) -> ModelType:
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def save(self, obj: ModelType) -> ModelType:
        """Commit pending changes and refresh the object."""
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, obj: ModelType) -> None:
        """Hard delete — use only for non-financial entities."""
        self.db.delete(obj)
        self.db.commit()
