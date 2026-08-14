from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Timestamped(ORMModel):
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Paginated(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    pages: int
    page_size: int


class ApiError(BaseModel):
    message: str
    code: str
    ref: str
    details: Any = None


class ErrorResponse(BaseModel):
    detail: ApiError


class Message(BaseModel):
    message: str
