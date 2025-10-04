"""Review API router."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request, Response
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from codereview_agent.common.exception.error_codes import ErrorCode
from codereview_agent.common.exception.exceptions import ErrorCodeException
from codereview_agent.review.schemas import ReviewRequest
from codereview_agent.review.service import ReviewService
from codereview_agent.review.api.openapi_docs import build_review_request_schema
from codereview_agent.common import ApiSuccessResponse

router = APIRouter()
review_service = ReviewService()


@router.post(
    "/reviews",
    openapi_extra={
        "requestBody": build_review_request_schema()
    },
)
async def request_code_review(raw_request: Request, response: Response):
    body_bytes = await raw_request.body()
    if not body_bytes:
        raise ErrorCodeException(
            ErrorCode.MISSING_ARGUMENT,
            errors=[
                {
                    "field": "body",
                    "message": ErrorCode.MISSING_ARGUMENT.message,
                }
            ],
        )

    raw_text = body_bytes.decode("utf-8")

    payload = _load_payload(raw_text)
    if payload is None:
        raise ErrorCodeException(
            ErrorCode.INVALID_ARGUMENT,
            errors=[
                {
                    "field": "body",
                    "message": ErrorCode.INVALID_ARGUMENT.message,
                }
            ],
        )

    try:
        request = ReviewRequest.model_validate(payload)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc

    data = review_service.generate_review(request)
    return ApiSuccessResponse(data=data)


def _load_payload(text: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(text, strict=False)
    except json.JSONDecodeError as exc:
        sanitized = _sanitize_control_chars(text)
        if sanitized != text:
            try:
                return json.loads(sanitized, strict=False)
            except json.JSONDecodeError:
                pass

        heuristic = _heuristic_parse_request(text)
        if heuristic is not None:
            return heuristic

        raise ErrorCodeException(
            ErrorCode.INVALID_ARGUMENT,
            message="요청 본문을 JSON으로 해석할 수 없습니다.",
            errors=[{"field": "body", "message": ErrorCode.INVALID_ARGUMENT.message}],
        ) from exc


def _sanitize_control_chars(text: str) -> str:
    result: list[str] = []
    in_string = False
    escape_next = False
    for char in text:
        if escape_next:
            result.append(char)
            escape_next = False
            continue

        if char == "\\":
            result.append(char)
            escape_next = True
            continue

        if char == '"':
            result.append(char)
            in_string = not in_string
            continue

        if in_string and char in {"\n", "\r"}:
            result.append("\\n" if char == "\n" else "\\r")
            continue

        result.append(char)

    return "".join(result)


def _heuristic_parse_request(text: str) -> Optional[Dict[str, Any]]:
    try:
        code_value = _extract_between_keys(text, "code", "language")
        language_value = _extract_simple_value(text, "language")
        style_value = _extract_simple_value(text, "style")
    except ValueError:
        return None

    payload: Dict[str, Any] = {"code": code_value}
    if language_value is not None:
        payload["language"] = language_value
    if style_value is not None:
        payload["style"] = style_value
    return payload


def _extract_between_keys(text: str, target_key: str, next_key: str) -> str:
    target_marker = f'"{target_key}"'
    next_marker = f'"{next_key}"'

    target_index = text.find(target_marker)
    if target_index == -1:
        raise ValueError("target key missing")

    after_colon = text.find(":", target_index)
    if after_colon == -1:
        raise ValueError("missing colon for target")

    start_quote = text.find('"', after_colon)
    if start_quote == -1:
        raise ValueError("missing opening quote for target")

    next_index = text.find(next_marker, start_quote)
    if next_index == -1:
        raise ValueError("next key missing")

    segment = text[start_quote + 1 : next_index]
    closing_quote_pos = segment.rfind('"')
    if closing_quote_pos == -1:
        raise ValueError("missing closing quote for target")

    raw_value = segment[:closing_quote_pos]
    return raw_value


def _extract_simple_value(text: str, key: str) -> Optional[str]:
    key_marker = f'"{key}"'
    key_index = text.find(key_marker)
    if key_index == -1:
        return None

    after_colon = text.find(":", key_index)
    if after_colon == -1:
        return None

    start_quote = text.find('"', after_colon)
    if start_quote == -1:
        return None

    end_quote = text.find('"', start_quote + 1)
    if end_quote == -1:
        return None

    return text[start_quote + 1 : end_quote]
