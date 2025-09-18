

# AGENTS.md

## CodeReviewAgent
- 목적: 사용자의 코드와 리뷰 스타일을 기반으로 개선 제안을 생성하고 구조화된 리뷰 결과를 반환합니다.
- 입력 구조 요약:
  - code: 사용자가 요청한 코드 (최대 500줄)
  - language: (선택) 코드 언어 (기본값: javascript)
  - style: 리뷰 스타일 (bug | detail | refactor | test)

- 출력 구조 요약:
  - sessionId: 리뷰 세션 고유 ID
  - originalCode: 요청된 원본 코드
  - currentCode: 적용된 코드 상태 (초기엔 원본과 동일)
  - summary: 주요 리뷰 요약 메시지
  - suggestions: 코드 개선 제안 목록
    - id, rationale, severity, range, fix 등 포함
  - metrics: (선택) 처리 시간, 사용 모델 정보

- 예시 요청:
```json
{
  "code": "function sum(a,b){ return a+b; }",
  "language": "javascript",
  "style": "bug"
}
```

- 예시 응답:
```json
{
  "sessionId": "abc-123",
  "originalCode": "...",
  "currentCode": "...",
  "summary": "가독성 개선 제안이 있습니다",
  "suggestions": [
    {
      "id": "uuid",
      "rationale": "명확한 함수명을 권장합니다",
      "severity": "minor",
      "range": { "startLine": 1, "startCol": 10, "endLine": 1, "endCol": 13 },
      "fix": {
        "type": "unified-diff",
        "diff": "--- a\n+++ b\n@@ -1 +1 @@\n-function sum\n+function calculateSum"
      },
      "fixSnippet": "function calculateSum(a, b) { return a + b; }",
      "confidence": 0.91,
      "status": "pending"
    }
  ],
  "metrics": {
    "processingTimeMs": 8132,
    "model": "claude-3-haiku"
  }
}
```