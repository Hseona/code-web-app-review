"""Schema for incoming review requests."""

from typing import Literal, Optional

from pydantic import BaseModel

__all__ = ["ReviewRequest"]


class ReviewRequest(BaseModel):
    code: str
    language: Optional[str] = None
    style: Literal["bug", "detail", "refactor", "test"] = "detail"
