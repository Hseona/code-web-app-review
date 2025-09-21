This project utilizes Codex and Claude Code.
# CodeReviewAgent

AI 기반 코드 리뷰 자동화 백엔드 API 서비스입니다. 빠르고 일관된 리뷰를 제공해 개인 및 소규모 팀의 개발 생산성을 높이는 것이 목표입니다.

## 기술 스택

- Python 3.10+
- FastAPI & Uvicorn
- Pydantic v2
- Poetry (의존성/패키징)
- Pytest (단위 테스트)

## 주요 기능

- POST `/api/reviews` 엔드포인트가 코드, 언어(선택), 리뷰 스타일을 받아 구조화된 리뷰 결과를 반환합니다.
- 요청 본문이 줄바꿈이나 따옴표를 이스케이프하지 않아도 라우터가 JSON을 정규화하고 휴리스틱으로 파싱합니다.
- `ReviewService`가 리뷰 스타일과 언어를 정규화하며 모델 입력을 500자로 제한해 Claude 3 Haiku 호출 안정성을 높입니다.
- Claude 응답이 비어 있거나 오류가 발생하면 `==` → `===`, `console.log` 정리, 설명 없는 `TODO`, 테스트 스캐폴드 제안을 포함한 휴리스틱 백업을 제공합니다.
- 모든 응답에 처리 시간과 사용된 모델명을 담은 `ReviewMetrics`가 포함됩니다.

## 아키텍처 개요

```
.
├── codereview_agent/
│   ├── app/               FastAPI 애플리케이션 초기화와 CORS 설정 (`main.py`, `run.py`)
│   ├── review/
│   │   ├── api/           `/api/reviews` 라우터, 본문 정규화, OpenAPI 문서
│   │   ├── config.py      `.env` 기반 Claude 설정 로더
│   │   ├── models/        응답 도메인 모델(`ReviewData`, `Suggestion`, `ReviewMetrics`)
│   │   ├── schemas/       Pydantic 요청·응답 스키마(`ReviewRequest`, `ReviewResponse`)
│   │   └── service/       Claude 연동 및 휴리스틱 백업 로직(`review_service.py`, `claude_client.py`)
├── tests/                 `ReviewService`와 라우터 회귀 테스트
├── pyproject.toml         Poetry 프로젝트 설정
└── test_main.http         HTTP 요청 시나리오 예시
```

## 리뷰 워크플로우

1. 클라이언트가 코드, 언어(선택), 리뷰 스타일(`bug`, `detail`, `refactor`, `test`)을 `/api/reviews`로 전송합니다.
2. FastAPI 라우터가 요청 본문을 JSON으로 파싱하고, 실패 시 개행/따옴표를 정규화한 뒤 휴리스틱으로 `code`·`language`·`style`을 추출합니다.
3. `ReviewRequest` 스키마가 입력을 검증하고 스타일/언어 값을 정규화합니다.
4. `ReviewService`가 리뷰 스타일을 확정하고 간단한 패턴 매칭으로 언어를 추론하며, 모델 입력 코드를 최대 500자까지 잘라 `ClaudeReviewClient`에 전달합니다.
5. Claude 호출이 성공하면 응답에서 요약·제안·메트릭을 정규화해 `ReviewData`로 변환하고, 누락된 요약은 스타일 프로필을 이용해 보완합니다.
6. Claude 호출이 실패하면 사유를 포함한 요약과 휴리스틱 제안 목록을 만들어 503 응답과 함께 반환합니다.

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
      "processingTimeMs": 42,
      "model": "claude-3-haiku-20240307"
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
CLAUDE_MAX_TOKENS=1200
CLAUDE_TEMPERATURE=0.0
```

추가 참고 사항:

- 환경 파일 템플릿은 `.env.example`에 있습니다.
- `CLAUDE_API_KEY`가 없으면 요청은 최대 3회 재시도 후 휴리스틱 기반 백업 결과와 함께 503을 반환합니다.
- API 응답의 `data.metrics.model` 값은 Claude 호출이 성공하면 모델명을, 실패 시 `codex-heuristic-v1`을 나타냅니다.
