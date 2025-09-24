"""Common shared utilities for the CodeReviewAgent service."""

from codereview_agent.common.error_codes import ErrorCode
from codereview_agent.common.exception_handlers import register_exception_handlers
from codereview_agent.common.exceptions import ErrorCodeException
from codereview_agent.common.messages import REMOTE_REVIEW_FAILURE_MESSAGE
from codereview_agent.common.response import (
    ApiErrorDetail,
    ApiErrorResponse,
    ApiSuccessResponse,
)

__all__ = [
    "ErrorCode",
    "ErrorCodeException",
    "ApiSuccessResponse",
    "ApiErrorResponse",
    "ApiErrorDetail",
    "register_exception_handlers",
    "REMOTE_REVIEW_FAILURE_MESSAGE",
]
