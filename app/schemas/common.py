from typing import Generic, List, TypeVar
from pydantic import BaseModel

DataT = TypeVar("DataT")


class PaginatedResponse(BaseModel, Generic[DataT]):
    """Standard paginated response wrapper used across all list endpoints."""
    items: List[DataT]
    total: int
    page: int
    size: int
    pages: int


class MessageResponse(BaseModel):
    """Simple success message response."""
    message: str


class ErrorResponse(BaseModel):
    """Standard error response shape."""
    detail: str
