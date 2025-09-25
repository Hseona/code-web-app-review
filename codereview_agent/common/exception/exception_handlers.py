"""FastAPI exception handlers that emit unified API error responses."""

from __future__ import annotations

from typing import Sequence

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from codereview_agent.common.exception.custom_internal_server_exception import (
    CustomInternalServerException,
)
from codereview_agent.common.exception.error_codes import ErrorCode
from codereview_agent.common.exception.exceptions import ErrorCodeException
from codereview_agent.common.response import ApiErrorDetail, ApiErrorResponse

_GENERAL_FIELD = "general"


def register_exception_handlers(app: FastAPI) -> None:
    """Register exception handlers mirroring the Spring configuration."""

    @app.exception_handler(CustomInternalServerException)
    async def handle_custom_internal_server_exception(
        request: Request, exc: CustomInternalServerException
    ) -> JSONResponse:
        detail = exc.detail or exc.code.message
        response = ApiErrorResponse.from_error_code(
            exc.code,
            message=exc.code.message,
            errors=_build_general_error(detail),
        )
        return JSONResponse(
            status_code=exc.code.status_code,
            content=response.model_dump(),
        )

    @app.exception_handler(ErrorCodeException)
    async def handle_error_code_exception(
        request: Request, exc: ErrorCodeException
    ) -> JSONResponse:
        errors = _ensure_details(exc.errors) if exc.errors else []
        response = ApiErrorResponse.from_error_code(
            exc.error_code,
            message=exc.message,
            errors=errors or _build_general_error(exc.message),
        )
        return JSONResponse(
            status_code=exc.error_code.status_code,
            content=response.model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = _convert_pydantic_errors(exc.errors())
        error_code = ErrorCode.INVALID_ARGUMENT
        response = ApiErrorResponse.from_error_code(
            error_code, errors=details
        )
        return JSONResponse(
            status_code=error_code.status_code,
            content=response.model_dump(),
        )

    @app.exception_handler(ValidationError)
    async def handle_validation_error(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        details = _convert_pydantic_errors(exc.errors())
        error_code = ErrorCode.INVALID_ARGUMENT
        response = ApiErrorResponse.from_error_code(
            error_code, errors=details
        )
        return JSONResponse(
            status_code=error_code.status_code,
            content=response.model_dump(),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        error_code = _map_status_to_error_code(exc.status_code)
        detail_message = _extract_detail_message(exc.detail) or error_code.message
        details = (
            exc.detail.get("errors")
            if isinstance(exc.detail, dict) and exc.detail.get("errors")
            else _build_general_error(detail_message)
        )
        response = ApiErrorResponse.from_error_code(
            error_code,
            message=detail_message,
            errors=_ensure_details(details),
        )
        return JSONResponse(
            status_code=error_code.status_code,
            content=response.model_dump(),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(
        request: Request, exc: Exception
    ) -> JSONResponse:
        error_code = ErrorCode.PROCESSING_ERROR
        response = ApiErrorResponse.from_error_code(
            error_code,
            message=error_code.message,
            errors=_build_general_error(str(exc) or error_code.message),
        )
        return JSONResponse(
            status_code=error_code.status_code,
            content=response.model_dump(),
        )


def _convert_pydantic_errors(errors: Sequence[dict[str, object]]) -> list[ApiErrorDetail]:
    return [
        ApiErrorDetail(
            field=_format_location(error.get("loc", ())),
            message=str(error.get("msg", "요청 본문이 올바르지 않습니다.")),
        )
        for error in errors
    ]


def _format_location(location: Sequence[object]) -> str:
    filtered = [str(part) for part in location if part != "body"]
    return ".".join(filtered) if filtered else _GENERAL_FIELD


def _build_general_error(message: str) -> list[ApiErrorDetail]:
    return [ApiErrorDetail(field=_GENERAL_FIELD, message=message)]


def _extract_detail_message(detail: object) -> str | None:
    if isinstance(detail, dict):
        message = detail.get("message")
        return str(message) if message is not None else None
    if isinstance(detail, str):
        return detail
    return None


def _ensure_details(
    errors: Sequence[ApiErrorDetail] | Sequence[dict[str, str]]
) -> list[ApiErrorDetail]:
    return [
        error if isinstance(error, ApiErrorDetail) else ApiErrorDetail(**error)
        for error in errors
    ]


def _map_status_to_error_code(status_code: int) -> ErrorCode:
    if status_code == ErrorCode.FORBIDDEN.status_code:
        return ErrorCode.FORBIDDEN
    if status_code == ErrorCode.NOT_FOUND.status_code:
        return ErrorCode.NOT_FOUND
    if status_code == ErrorCode.TOO_MANY_REQUESTS.status_code:
        return ErrorCode.TOO_MANY_REQUESTS
    if status_code == ErrorCode.SERVICE_UNAVAILABLE.status_code:
        return ErrorCode.SERVICE_UNAVAILABLE
    if status_code >= 500:
        return ErrorCode.PROCESSING_ERROR
    return ErrorCode.BAD_REQUEST
