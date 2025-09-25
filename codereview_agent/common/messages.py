"""Text templates shared across the service."""

from __future__ import annotations

REMOTE_REVIEW_FAILURE_MESSAGE = (
    "Claude API 호출에 실패했습니다. 잠시 후 다시 시도해주세요. "
)

__all__ = ["REMOTE_REVIEW_FAILURE_MESSAGE"]
