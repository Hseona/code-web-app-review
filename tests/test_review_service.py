import pytest

from codereview_agent.review.schemas import ReviewRequest
from codereview_agent.review.service import ReviewService


@pytest.fixture()
def review_service() -> ReviewService:
    return ReviewService()


def test_generate_review_bug_style_detects_multiple_issues(review_service: ReviewService) -> None:
    code = """function compare(a, b) {
  if (a == b) {
    console.log('equal');
  }
}
"""
    request = ReviewRequest(code=code, style="bug")

    response = review_service.generate_review(request)

    assert response.code == 200
    assert "버그 중심" in response.data.summary
    assert "JAVASCRIPT" in response.data.summary

    titles = {suggestion.title for suggestion in response.data.suggestions}
    assert "동등 연산자 강화" in titles
    assert "디버그 로그 정리" in titles


def test_generate_review_test_style_adds_scaffold(review_service: ReviewService) -> None:
    code = """export function sum(a, b) {
  return a + b;
}
"""
    request = ReviewRequest(code=code, style="test")

    response = review_service.generate_review(request)

    assert response.code == 200
    assert "테스트 중심" in response.data.summary

    titles = [suggestion.title for suggestion in response.data.suggestions]
    assert titles == ["테스트 스캐폴드 추가"]

    snippet = response.data.suggestions[0].fix_snippet
    assert "describe('module'" in snippet
    assert "it('should do something meaningful'" in snippet


def test_generate_review_detects_typescript_language(review_service: ReviewService) -> None:
    code = """interface User {
  id: number;
  name: string;
}
"""
    request = ReviewRequest(code=code)

    response = review_service.generate_review(request)

    assert response.code == 200
    assert "TYPESCRIPT" in response.data.summary
    assert response.data.suggestions == []
