from __future__ import annotations

from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    pages: int
    page_size: int


def page_params(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> tuple[int, int]:
    return page, page_size


def build_page(items: list[T], total: int, page: int, page_size: int) -> Page[T]:
    return Page(items=items, total=total, page=page, pages=max(1, -(-total // page_size)), page_size=page_size)
