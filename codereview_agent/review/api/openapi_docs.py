"""OpenAPI helper utilities for review endpoints."""

from __future__ import annotations

from typing import Any, Dict

from codereview_agent.review.schemas import ReviewRequest


def build_review_request_schema() -> Dict[str, Any]:
    """Return the JSON schema for review requests with example payloads."""

    schema = ReviewRequest.model_json_schema(
        ref_template="#/components/schemas/{model}"
    )

    return {
        "required": True,
        "content": {
            "application/json": {
                "schema": schema,
                "examples": {
                    "multiline": {
                        "summary": "여러 줄 코드 예시",
                        "value": {
                            "code": "print('hello')\nprint('world')",
                            "language": "python",
                            "style": "bug",
                        },
                    }
                },
            }
        },
    }

