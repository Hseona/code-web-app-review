import pytest

from fastapi.testclient import TestClient

from codereview_agent.app.main import codeReviewAgent
from codereview_agent.review.schemas import ReviewRequest
from codereview_agent.review.service import ReviewService, ReviewServiceError
from codereview_agent.review.service.claude_client import ClaudeReviewError


class RecordingClaudeClient:
    def __init__(self) -> None:
        self.model_name = "claude-3-haiku-20240307"
        self.calls = []

    def create_review(self, request, *, language: str, style: str, code: str):
        self.calls.append({"language": language, "style": style, "code": code})
        return {
            "summary": "Remote review summary",
            "suggestions": [
                {
                    "id": "stub-1",
                    "title": "Stub Suggestion",
                    "rationale": "Example remote rationale",
                    "severity": "major",
                    "tags": ["remote", "test"],
                    "range": {
                        "startLine": 1,
                        "startCol": 1,
                        "endLine": 1,
                        "endCol": 1,
                    },
                    "fix": {"type": "unified-diff", "diff": "--- a\n+++ b"},
                    "fixSnippet": "updated();",
                    "confidence": 0.9,
                    "status": "pending",
                }
            ],
            "metrics": {"processingTimeMs": 42, "model": self.model_name},
        }


class FailingClaudeClient:
    def __init__(self) -> None:
        self.model_name = "claude-3-haiku-20240307"

    def create_review(self, request, *, language: str, style: str, code: str):  # noqa: ARG002 - interface parity
        raise ClaudeReviewError("네트워크 오류")


class TypeScriptRecordingClient:
    def __init__(self) -> None:
        self.model_name = "claude-3-haiku-20240307"
        self.last_call = None

    def create_review(self, request, *, language: str, style: str, code: str):
        self.last_call = {"language": language, "style": style, "code": code}
        return {
            "summary": f"{language.upper()} remote summary",
            "suggestions": [],
            "metrics": {"model": self.model_name},
        }


def test_generate_review_success_uses_remote_payload():
    client = RecordingClaudeClient()
    service = ReviewService(review_client=client)

    code = """function sum(a, b) {\n  return a + b;\n}\n"""
    request = ReviewRequest(code=code, style="bug")

    data = service.generate_review(request)

    assert data.summary == "Remote review summary"
    assert data.metrics.model == client.model_name
    assert data.metrics.processing_time_ms == 42
    assert len(data.suggestions) == 1
    assert client.calls and client.calls[0]["language"] == "javascript"
    assert client.calls[0]["style"] == "bug"
    assert client.calls[0]["code"] == code


def test_generate_review_failure_returns_fallback_suggestions():
    client = FailingClaudeClient()
    service = ReviewService(review_client=client)

    code = """function compare(a, b) {\n  if (a == b) {\n    console.log('equal');\n  }\n}\n"""
    request = ReviewRequest(code=code, style="bug")

    with pytest.raises(ReviewServiceError) as exc_info:
        service.generate_review(request)

    error = exc_info.value.response
    assert error.code == 503
    assert "내부 휴리스틱 결과" in error.message
    assert [detail.model_dump() for detail in error.errors] == [
        {"field": "claude", "message": "네트워크 오류"},
    ]

    titles = {suggestion.title for suggestion in exc_info.value.suggestions}
    assert "동등 연산자 강화" in titles
    assert "디버그 로그 정리" in titles


def test_generate_review_detects_typescript_language():
    client = TypeScriptRecordingClient()
    service = ReviewService(review_client=client)

    code = """interface User {\n  id: number;\n  name: string;\n}\n"""
    request = ReviewRequest(code=code)

    data = service.generate_review(request)

    assert data.summary == "TYPESCRIPT remote summary"
    assert client.last_call == {"language": "typescript", "style": "detail", "code": code}
    assert data.metrics.model == client.model_name
    assert data.suggestions == []


def test_generate_review_truncates_code_for_remote_payload():
    class RecordingClient:
        model_name = "claude-3-haiku-20240307"

        def __init__(self) -> None:
            self.last_code = None

        def create_review(self, request, *, language: str, style: str, code: str):  # noqa: ARG002
            self.last_code = code
            return {
                "summary": "ok",
                "suggestions": [],
                "metrics": {"model": self.model_name},
            }

    long_code = "function main() {\n" + ("const value = 1;\n" * 300) + "}\n"
    request = ReviewRequest(code=long_code)
    service = ReviewService(review_client=RecordingClient())

    service.generate_review(request)

    assert len(service._review_client.last_code) == 500
    assert service._review_client.last_code == long_code[:500]


def test_api_route_accepts_multiline_code_payload(monkeypatch):
    class AcceptingClient:
        model_name = "claude-3-haiku-20240307"

        def __init__(self) -> None:
            self.last_code = None

        def create_review(self, request, *, language: str, style: str, code: str):  # noqa: ARG002
            self.last_code = code
            return {
                "summary": "ok",
                "suggestions": [],
                "metrics": {"model": self.model_name},
            }

    service = ReviewService(review_client=AcceptingClient())

    monkeypatch.setattr("codereview_agent.review.api.review_router.review_service", service)

    client = TestClient(codeReviewAgent)
    payload = {
        "code": "def foo():\n    return 1",
        "language": "python",
        "style": "bug",
    }

    response = client.post("/api/reviews", json=payload)

    assert response.status_code == 200
    original_code = "def foo():\n    return 1"
    body = response.json()
    assert body["code"] == 200
    assert service._review_client.last_code == original_code


def test_api_route_handles_unescaped_newlines(monkeypatch):
    class AcceptingClient:
        model_name = "claude-3-haiku-20240307"

        def __init__(self) -> None:
            self.last_code = None

        def create_review(self, request, *, language: str, style: str, code: str):  # noqa: ARG002
            self.last_code = code
            return {
                "summary": "ok",
                "suggestions": [],
                "metrics": {"model": self.model_name},
            }

    service = ReviewService(review_client=AcceptingClient())
    monkeypatch.setattr("codereview_agent.review.api.review_router.review_service", service)

    client = TestClient(codeReviewAgent)
    raw_payload = '{"code": "def foo():\n    return 1", "language": "python", "style": "bug"}'

    response = client.post(
        "/api/reviews",
        content=raw_payload,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 200
    assert response.json()["code"] == 200
    assert service._review_client.last_code == "def foo():\n    return 1"


def test_api_route_handles_unescaped_quotes_and_newlines(monkeypatch):
    class AcceptingClient:
        model_name = "claude-3-haiku-20240307"

        def __init__(self) -> None:
            self.last_code = None

        def create_review(self, request, *, language: str, style: str, code: str):  # noqa: ARG002
            self.last_code = code
            return {
                "summary": "ok",
                "suggestions": [],
                "metrics": {"model": self.model_name},
            }

    service = ReviewService(review_client=AcceptingClient())
    monkeypatch.setattr("codereview_agent.review.api.review_router.review_service", service)

    client = TestClient(codeReviewAgent)
    raw_payload = '''{
  "code": "def generate_review(self, request: ReviewRequest) -> ApiSuccessResponse[ReviewData]:
        start_time = time.perf_counter()
        style = self._normalize_style(request.style)
        language = self._resolve_language(request.language, request.code)

        client = self._review_client or ClaudeReviewClient()
        self._review_client = client

        try:
            remote_payload = client.create_review(
                request,
                language=language,
                style=style,
            )
            data = self._build_remote_data(
                request=request,
                style=style,
                language=language,
                remote_payload=remote_payload,
                client=client,
                started_at=start_time,
            )
            return ApiSuccessResponse[ReviewData](code=200, message="OK", data=data)
        except ClaudeReviewError as exc:
            suggestions = self._collect_suggestions(request.code, style)
            fallback_summary = self._build_summary(style, language, suggestions)
            summary = (
                "Claude API 호출에 실패했습니다. 잠시 후 다시 시도해주세요. "
                f"(사유: {exc.user_message}) 내부 휴리스틱 결과를 제공합니다. {fallback_summary}"
            )
            processing_ms = int((time.perf_counter() - start_time) * 1000)

            data = ReviewData(
                session_id=str(uuid4()),
                original_code=request.code,
                current_code=request.code,
                summary=summary,
                suggestions=suggestions,
                metrics=ReviewMetrics(
                    processing_time_ms=processing_ms,
                    model=FALLBACK_MODEL_NAME,
                ),
            )

            return ApiSuccessResponse[ReviewData](
                code=503,
                message="Claude API 호출 실패",
                data=data,
            )",
  "language": "python",
  "style": "bug"
}'''

    response = client.post(
        "/api/reviews",
        content=raw_payload,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 200
    assert response.json()["code"] == 200
    # assert 'message = "Hello, " + name + "!"' in service._review_client.last_code


def test_api_route_returns_error_payload_on_service_failure(monkeypatch):
    class FailingClient:
        model_name = "claude-3-haiku-20240307"

        def create_review(self, request, *, language: str, style: str, code: str):  # noqa: ARG002
            raise ClaudeReviewError("네트워크 오류")

    service = ReviewService(review_client=FailingClient())
    monkeypatch.setattr("codereview_agent.review.api.review_router.review_service", service)

    client = TestClient(codeReviewAgent)
    payload = {
        "code": "function test() { return 1 }",
        "language": "javascript",
        "style": "bug",
    }

    response = client.post("/api/reviews", json=payload)

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "SERVICE_UNAVAILABLE"
    assert body["code"] == 503
    assert "내부 휴리스틱 결과" in body["message"]
    assert body["errors"] == [{"field": "claude", "message": "네트워크 오류"}]


def test_review_request_normalizes_style_and_language():
    request = ReviewRequest.model_validate(
        {
            "code": "print('ok')",
            "language": " Python  ",
            "style": "Bug",
        }
    )

    assert request.style == "bug"
    assert request.language == "Python"
