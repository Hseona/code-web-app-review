"""Enumerates canonical error codes used across the service."""

from __future__ import annotations

from enum import Enum
from http import HTTPStatus


class ErrorCode(Enum):
    """Domain-specific error codes guarded by HTTP status metadata."""

    DUPLICATE_ARGUMENT = (
        HTTPStatus.BAD_REQUEST,
        101,
        "해당 값은 이미 존재합니다.",
    )
    INVALID_DATE_FORMAT = (
        HTTPStatus.BAD_REQUEST,
        102,
        "날짜 형식이 올바르지 않습니다. 'yyyy-MM-dd HH:mm:ss' 형식으로 입력해주세요.",
    )
    INVALID_ARGUMENT = (
        HTTPStatus.BAD_REQUEST,
        103,
        "필수값이 누락 되었거나 요청 형식이 유효하지 않습니다.",
    )
    JSON_PROCESS_ERROR = (
        HTTPStatus.BAD_REQUEST,
        104,
        "데이터 처리 중 문제가 발생했습니다.",
    )
    EXPIRED = (HTTPStatus.BAD_REQUEST, 105, "기간이 만료되었습니다.")
    DUPLICATE_REQUEST = (
        HTTPStatus.BAD_REQUEST,
        106,
        "이미 처리된 요청입니다.",
    )
    MISSING_ARGUMENT = (
        HTTPStatus.BAD_REQUEST,
        107,
        "필수값이 누락되었습니다.",
    )
    BAD_REQUEST = (
        HTTPStatus.BAD_REQUEST,
        108,
        "요청 처리 중 문제가 발생했습니다.",
    )
    FORBIDDEN = (
        HTTPStatus.FORBIDDEN,
        403,
        "요청하신 작업을 처리할 수 없습니다.",
    )
    NOT_FOUND = (
        HTTPStatus.NOT_FOUND,
        404,
        "해당 정보를 찾을 수 없습니다",
    )
    TOO_MANY_REQUESTS = (
        HTTPStatus.TOO_MANY_REQUESTS,
        429,
        "잠시 후 다시 시도해주세요.",
    )
    SERVICE_UNAVAILABLE = (
        HTTPStatus.SERVICE_UNAVAILABLE,
        503,
        "서비스 이용이 원활하지 않습니다. 잠시 후 다시 시도해주세요.",
    )
    PROCESSING_ERROR = (
        HTTPStatus.INTERNAL_SERVER_ERROR,
        500,
        "처리 중 문제가 발생했습니다.",
    )

    def __init__(self, status: HTTPStatus, code: int, message: str) -> None:
        self.status = status
        self.code = code
        self.message = message

    @property
    def status_code(self) -> int:
        """Return the HTTP status code value."""
        return self.status.value

    @property
    def status_label(self) -> str:
        """Return the HTTP status name for serialization."""
        return self.status.name
