"""Custom exceptions that wrap ErrorCode metadata."""

from __future__ import annotations

from typing import Iterable, Sequence

from codereview_agent.common.exception.error_codes import ErrorCode


class ErrorCodeException(Exception):
    """Exception carrying an ErrorCode with optional error entries."""

    def __init__(
        self,
        error_code: ErrorCode,
        *,

        message: str | None = None,
        errors: Sequence[object] | Iterable[object] | None = None,
    ) -> None:
        self.error_code = error_code
        self.message = message or error_code.message
        self.errors = list(errors or [])
        super().__init__(self.message)

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return self.message
