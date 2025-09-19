# AGENTS.md

## CodeReviewAgent
- 목적: 사용자의 코드와 선택한 리뷰 스타일을 바탕으로 구조화된 제안 리스트를 생성하고, 제안별 패치와 사유를 함께 제공합니다.
- 동작 요약:
  - 입력으로 코드(최대 500줄), 선택적 언어, 리뷰 스타일(`bug`, `detail`, `refactor`, `test`)을 받습니다.
  - 스타일 프로필에 따라 비엄격 비교(`==`), `console.log`, 설명 없는 `TODO`, 테스트 부재 등 휴리스틱을 점검합니다.
  - 제안(`Suggestion`) 단위로 범위, 심각도, 태그, 패치(diff)를 생성하고 `ReviewResponse` 구조에 담아 반환합니다.
  - 처리 시간과 내부 모델명을 `metrics`에 기록해 SLA 모니터링과 추후 학습 데이터로 활용합니다.

- 입력 구조:
  - `code`: 리뷰 대상 코드 문자열 (필수)
  - `language`: 언어 명시 (선택, 미제공 시 단순 휴리스틱으로 추정)
  - `style`: 리뷰 스타일 프로필 (`bug` | `detail` | `refactor` | `test`)

- 출력 구조 (`ReviewResponse`):
  - `code`: HTTP 상태 코드 값 전달용 정수 (예: 200)
  - `message`: 처리 결과 메시지 (`"OK"` 등)
  - `data`: 리뷰 결과 페이로드
    - `sessionId`: 리뷰 세션 고유 ID (UUID)
    - `originalCode`: 입력 코드 원문
    - `currentCode`: 제안 적용 전 코드 (초기엔 원문과 동일)
    - `summary`: 스타일 프로필과 언어 관점의 리뷰 요약
    - `suggestions`: 제안 리스트
      - `id`, `title`, `rationale`, `severity`, `tags`
      - `range`: `startLine`, `startCol`, `endLine`, `endCol`
      - `fix`: `type`(예: `unified-diff`), `diff`
      - `fixSnippet`: 적용 결과 스니펫
      - `confidence`: 0~1 사이 신뢰도
      - `status`: `pending` | `accepted` | `rejected`
    - `metrics`: `processingTimeMs`, `model`

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
  "code": 200,
  "message": "OK",
  "data": {
    "sessionId": "abc-123",
    "originalCode": "function sum(a,b){ return a+b }",
    "currentCode": "function sum(a,b){ return a+b }",
    "summary": "버그 중심 관점에서 1개의 제안을 생성했습니다.",
    "suggestions": [
      {
        "id": "uuid",
        "title": "함수 네이밍 개선",
        "rationale": "명확한 함수명을 권장합니다",
        "severity": "minor",
        "tags": ["readability"],
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
      "model": "codex-heuristic-v1"
    }
  }
}
```
