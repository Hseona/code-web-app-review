"""Pydantic response schemas shared across the service."""

from __future__ import annotations

from typing import Generic, Iterable, Sequence, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from codereview_agent.common.exception.error_codes import ErrorCode

TData = TypeVar("TData")


class ApiSuccessResponse(BaseModel, Generic[TData]):
    code: int = 200
    message: str = "OK"
    data: TData

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class ApiErrorDetail(BaseModel):
    field: str
    message: str

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class ApiErrorResponse(BaseModel):
    status: str
    code: int
    message: str
    errors: list[ApiErrorDetail] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    @classmethod
    def from_error_code(
        cls,
        error_code: ErrorCode,
        *,
        message: str | None = None,
        errors: Sequence[ApiErrorDetail] | Iterable[ApiErrorDetail] | None = None,
    ) -> "ApiErrorResponse":
        """Factory that fills the response using an ErrorCode."""
        detail_errors = list(errors or [])
        return cls(
            status=error_code.status_label,
            code=error_code.status_code,
            message=message or error_code.message,
            errors=detail_errors,
        )

