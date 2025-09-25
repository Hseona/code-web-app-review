"""Common shared utilities for the CodeReviewAgent service."""

from codereview_agent.common.exception.custom_internal_server_exception import (
    CustomInternalServerException,
)
from codereview_agent.common.exception.error_codes import ErrorCode
from codereview_agent.common.exception.exception_handlers import register_exception_handlers
from codereview_agent.common.exception.exceptions import ErrorCodeException
from codereview_agent.common.messages import REMOTE_REVIEW_FAILURE_MESSAGE
from codereview_agent.common.response import (
    ApiErrorDetail,
    ApiErrorResponse,
    ApiSuccessResponse,
)

__all__ = [
    "ApiSuccessResponse",
    "ApiErrorResponse",
    "ApiErrorDetail",
]
