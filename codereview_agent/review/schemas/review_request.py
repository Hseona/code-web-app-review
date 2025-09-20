"""Schema for incoming review requests."""

from typing import Literal, Optional

from pydantic import BaseModel, field_validator

__all__ = ["ReviewRequest"]


class ReviewRequest(BaseModel):
    code: str
    language: Optional[str] = None
    style: Literal["bug", "detail", "refactor", "test"] = "detail"

    @field_validator("code")
    @classmethod
    def _ensure_code_not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            msg = "code 필드는 비어 있을 수 없습니다."
            raise ValueError(msg)
        return value

    @field_validator("language")
    @classmethod
    def _normalize_language(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("style", mode="before")
    @classmethod
    def _normalize_style(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return str(value).strip().lower() or None
