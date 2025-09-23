"""API response wrappers for success and error payloads."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict


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
    errors: list[ApiErrorDetail]

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
