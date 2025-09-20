This project utilizes Codex and Claude Code.
# CodeReviewAgent

AI 기반 코드 리뷰 자동화 백엔드 API 서비스입니다. <br>
빠르고 일관된 리뷰를 제공해 개인 및 소규모 팀의 개발 생산성을 높이는 것이 목표입니다.

## 기술 스택

- Python 3.10+
- FastAPI & Uvicorn
- Pydantic v2
- Poetry (의존성/패키징)
- Pytest (단위 테스트)

## 아키텍처 개요

- `review/api` – FastAPI 라우터와 엔드포인트 정의 (`/api/reviews`), 비정상 JSON 요청을 정규화한 뒤 비즈니스 서비스로 전달.
- `review/schemas` – 요청·응답 스키마(`ReviewRequest`, `ReviewResponse`).
- `review/models` – 리뷰 결과에 포함되는 제안·메트릭 등 도메인 모델.
- `review/service` – `ReviewService`가 Claude 3 Haiku 호출·재시도 및 휴리스틱 기반 백업 로직을 포함해 핵심 비즈니스 로직을 처리.
- `review/service/claude_client.py` – Anthropic Claude 3 Haiku API와의 통신, 재시도, 응답 정규화를 담당.
- `review/config.py` – `.env` / 환경 변수 기반 Claude 설정 로더.
- `tests` – `ReviewService` 동작을 검증하는 Pytest 케이스.

```
codereview_agent/
├── app/
│   ├── main.py
│   └── run.py
├── review/
│   ├── api/
│   │   └── router.py
│   ├── models/
│   │   ├── review_data.py
│   │   ├── review_examples.py
│   │   ├── review_metrics.py
│   │   └── suggestion.py
│   ├── schemas/
│   │   ├── ReviewRequest.py
│   │   └── ReviewResponse.py
│   └── service/
│       └── service.py
└── tests/
    └── test_review_service.py
```

## 리뷰 워크플로우

1. 클라이언트가 코드, 언어(선택), 리뷰 스타일(`bug`, `detail`, `refactor`, `test`)을 `/api/reviews`로 전송합니다. 줄바꿈이나 따옴표가 이스케이프되지 않은 경우라도 라우터가 자동으로 정규화합니다.
2. `ReviewService`가 스타일 프로필을 정규화하고 간단한 휴리스틱으로 언어를 감지한 뒤 Claude 3 Haiku API에 동일한 정보를 전달합니다. API 호출은 최대 3회 재시도합니다.
3. Claude 응답이 정상적이면 모델이 생성한 요약·제안·메트릭을 그대로 사용합니다. 실패 시 기존 휴리스틱(아래 제안 빌더)을 백업으로 실행합니다.
4. 스타일에 따라 다음 제안 빌더를 실행합니다.
   - 비엄격 비교(`==`)를 엄격 비교(`===`)로 교체 제안
   - `console.log` 정리 안내
   - 설명이 없는 `TODO` 주석 보강
   - 테스트 스타일 선택 시 테스트 스캐폴드 추가 권장
5. 제안, 요약, 처리 시간(`ReviewMetrics`)을 포함한 구조화 응답을 반환합니다. Claude 호출 실패 시 HTTP 응답 코드는 503으로, 메시지에 실패 사유와 휴리스틱 요약이 포함됩니다.
6. 향후 Accept/Reject 결과를 활용해 모델 개선을 목표로 합니다.

## 리뷰 스타일 프로필

| 스타일 | 요약 라벨 | 주요 목적 |
| --- | --- | --- |
| bug | 버그 중심 | 명확한 오류/버그 탐지 |
| detail | 디테일 중심 | 가독성·일관성 개선 |
| refactor | 리팩터링 중심 | 구조·클린 코드 관점 강화 |
| test | 테스트 중심 | 테스트 보강 및 검증 강조 |

## 실행 방법

```bash
# 의존성 설치
poetry install

# 가상환경 활성화
poetry shell

# 서버 실행
uvicorn codereview_agent.app.run:codeReviewAgent --reload
```

## 테스트

```bash
poetry run pytest
```

제한된 환경에서 임시 디렉터리에 접근할 수 없다면 `TMPDIR=/path/to/tmp poetry run pytest` 또는 `pytest --capture=no` 옵션을 사용해 주세요.

## API 예시

### POST `/api/reviews`

```json
{
  "code": "function sum(a, b) {\n  return a + b;\n }",
  "language": "javascript",
  "style": "bug"
}
```

```json
{
  "code": 200,
  "message": "OK",
  "data": {
    "sessionId": "abc-123",
    "originalCode": "...",
    "currentCode": "...",
    "summary": "...",
    "suggestions": [
      {
        "id": "uuid",
        "title": "동등 연산자 강화",
        "severity": "major",
        "tags": ["bug", "best-practice"],
        "range": {
          "startLine": 1,
          "startCol": 10,
          "endLine": 1,
          "endCol": 12
        },
        "fix": { "type": "unified-diff", "diff": "..." }
      }
    ],
    "metrics": {
      "processingTimeMs": 15,
      "model": "codex-heuristic-v1"
    }
  }
}
```

## 문서화

- Swagger: `http://localhost:8000/docs`

## Claude API 연동

이 프로젝트는 Claude 3 Haiku API를 기본 리뷰 엔진으로 사용합니다. 환경 변수 또는 `.env` / `.env.local` 파일에 다음 값을 설정하세요.

```
CLAUDE_API_KEY=your-api-key
CLAUDE_API_URL=https://api.anthropic.com            # /v1/messages까지 포함된 값도 허용됩니다.
CLAUDE_MODEL=claude-3-haiku-20240307
CLAUDE_TIMEOUT_SECONDS=30
CLAUDE_MAX_ATTEMPTS=3
CLAUDE_RETRY_DELAY_SECONDS=0.5
CLAUDE_MAX_TOKENS=2048
CLAUDE_TEMPERATURE=0.0
```

추가 참고 사항:

- 환경 파일 템플릿은 `.env.example`에 있습니다.
- `CLAUDE_API_KEY`가 없으면 요청은 최대 3회 재시도 후 휴리스틱 기반 백업 결과와 함께 503을 반환합니다.
- API 응답의 `data.metrics.model` 값은 Claude 호출이 성공하면 모델명을, 실패 시 `codex-heuristic-v1`을 나타냅니다.
