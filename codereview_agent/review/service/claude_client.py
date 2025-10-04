"""HTTP client integration for Claude 3 Haiku."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Optional, TYPE_CHECKING
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


if TYPE_CHECKING:  # pragma: no cover - type checking helper
    from codereview_agent.review.schemas import ReviewRequest

from codereview_agent.review.config import get_settings


logger = logging.getLogger(__name__)


REVIEW_PROMPT_INSTRUCTIONS = """You are a code review assistant that returns structured JSON responses.

Your response must strictly follow this schema:

{
  "sessionId": string,
  "originalCode": string,
  "currentCode": string,
  "summary": string,
  "suggestions": [
    {
      "id": string,
      "title": string,
      "rationale": string,
      "severity": "info" | "minor" | "major" | "critical",
      "tags": string[],
      "range": {
        "startLine": number,
        "startCol": number,
        "endLine": number,
        "endCol": number
      },
      "fix": {
        "type": "unified-diff",
        "diff": string
      },
      "fixSnippet": string,
      "confidence": number,
      "status": "pending"
    }
  ],
  "metrics": {
    "processingTimeMs": number,
    "model": string
  }
}

Notes:
- Use the exact field names and types above.
- `suggestions` must be a flat array of suggestion objects.
- All suggestion objects must include a unique `id`, a `rationale`, and a `range`.
- If any value is missing, return a default: empty string (`""`) or empty array (`[]`) or `null`, but do not omit the field.
- `status` is always `"pending"` by default.
- Set `confidence` to a float between 0.0 and 1.0, e.g. `0.85`.
- `fix.type` must always be `"unified-diff"` even if diff is empty.
- Include all fields even if the suggestion is minimal.
- Your output must be a **valid JSON object**, without commentary or explanation.

Do not wrap the JSON in Markdown or any prose."""

class ClaudeReviewError(Exception):
    """Raised when Claude API integration fails."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        cause: Optional[BaseException] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.cause = cause

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message

    @property
    def user_message(self) -> str:
        return self.message


class ClaudeReviewClient:
    """Lightweight HTTP client for the Claude 3 Haiku messages API."""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
        max_attempts: Optional[int] = None,
        retry_delay_seconds: Optional[float] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> None:
        settings = get_settings()

        self._api_key = api_key or settings.api_key
        configured_base = (base_url or settings.base_url).rstrip("/")
        if configured_base.endswith("/v1/messages"):
            configured_base = configured_base[: -len("/v1/messages")]
        self._base_url = configured_base.rstrip("/")
        self._model = model or settings.model
        self._timeout = timeout or settings.timeout_seconds
        self._max_attempts = max(1, max_attempts or settings.max_attempts)
        self._retry_delay = max(0.0, retry_delay_seconds or settings.retry_delay_seconds)
        self._max_tokens = max_tokens or settings.max_tokens
        self._temperature = temperature if temperature is not None else settings.temperature

    @property
    def model_name(self) -> str:
        return self._model

    def create_review(
        self,
        request: "ReviewRequest",
        *,
        language: str,
        style: str,
        code: str | None = None,
    ) -> Dict[str, Any]:
        """Request a structured review payload from Claude."""

        payload = self._build_payload(
            request,
            language=language,
            style=style,
            code=code or request.code,
        )

        last_error: Optional[ClaudeReviewError] = None
        for attempt in range(1, self._max_attempts + 1):
            try:
                return self._send(payload)
            except ClaudeReviewError as exc:
                last_error = exc
                if attempt < self._max_attempts:
                    time.sleep(self._retry_delay)

        if last_error is not None:
            raise last_error
        raise ClaudeReviewError("Claude API 호출에 실패했습니다.")

    # ------------------------------------------------------------------

    def _build_payload(
        self,
        request: "ReviewRequest",
        *,
        language: str,
        style: str,
        code: str,
    ) -> Dict[str, Any]:
        request_snapshot = {
            "code": code,
            "language": request.language,
            "resolvedLanguage": language,
            "style": style,
        }
        user_prompt_lines = [
            REVIEW_PROMPT_INSTRUCTIONS,
            "",
            "Review request context:",
            json.dumps(request_snapshot, ensure_ascii=True, indent=2),
            "Code snippet:",
            f"```{language or 'text'}\n{code}\n```",
        ]

        system_prompt = (
            "You are CodeReviewAgent. Review the supplied code in the requested style and language. "
            "Follow all schema requirements exactly and respond with valid JSON only."
        )

        return {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
            "system": system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "\n".join(user_prompt_lines),
                        }
                    ],
                },
            ],
        }

    def _send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self._api_key:
            raise ClaudeReviewError("Claude API 키가 설정되어 있지 않습니다.")

        data = json.dumps(payload).encode("utf-8")
        url = f"{self._base_url}/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
        }

        request = Request(url=url, data=data, headers=headers, method="POST")

        try:
            with urlopen(request, timeout=self._timeout) as response:
                raw_body = response.read().decode("utf-8")
        except HTTPError as exc:  # pragma: no cover - network failure handling
            error_body = exc.read().decode("utf-8", errors="ignore") if exc.fp else ""
            message = f"Claude API HTTP 오류 {exc.code}"
            if error_body:
                message = f"{message}: {error_body}"
            raise ClaudeReviewError(message, status_code=exc.code, cause=exc) from exc
        except URLError as exc:  # pragma: no cover - network failure handling
            raise ClaudeReviewError("Claude API 네트워크 오류", cause=exc) from exc
        except Exception as exc:  # pragma: no cover - defensive catch-all
            raise ClaudeReviewError("Claude API 호출 중 알 수 없는 오류가 발생했습니다.", cause=exc) from exc

        try:
            envelope = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise ClaudeReviewError("Claude API 응답을 JSON으로 파싱할 수 없습니다.", cause=exc) from exc

        return self._extract_review_payload(envelope)

    def _extract_review_payload(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        content = envelope.get("content")
        if not isinstance(content, list):
            raise ClaudeReviewError("Claude API 응답에 content 필드가 없습니다.")

        text_fragments = [
            fragment.get("text", "")
            for fragment in content
            if isinstance(fragment, dict) and fragment.get("type") == "text"
        ]
        combined = "".join(text_fragments).strip()
        if not combined:
            raise ClaudeReviewError("Claude API 응답에 텍스트 콘텐츠가 없습니다.")

        cleaned = self._strip_code_fences(combined)

        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ClaudeReviewError("Claude API 응답 JSON 형식이 올바르지 않습니다.", cause=exc) from exc

        if "data" in payload and isinstance(payload["data"], dict):
            return payload["data"]

        if not isinstance(payload, dict):
            raise ClaudeReviewError("Claude API 응답이 객체 형태가 아닙니다.")

        return payload

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        if not text.startswith("```"):
            return text

        lines = text.strip().splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()
