"""Custom internal server exception mirroring the Java runtime wrapper."""

from __future__ import annotations

from typing import Optional

from codereview_agent.common.exception.error_codes import ErrorCode


class CustomInternalServerException(Exception):
    """Runtime-style exception carrying an ErrorCode and optional detail message."""

    def __init__(self, error_code: ErrorCode, detail: str | None = None) -> None:
        super().__init__(error_code.message)
        self.code = error_code
        self._detail = detail

    @property
    def detail(self) -> Optional[str]:
        return self._detail

    def get_detail(self) -> Optional[str]:
        return self._detail
