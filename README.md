This project utilizes Codex and Claude Code.

# CodeReviewAgent

AI 기반 코드 리뷰 자동화 백엔드 API 서비스입니다.

## 기술 스택

- Python 3.9+
- FastAPI
- Uvicorn
- Pydantic
- Poetry (의존성 관리)

## AI Tools

- OpenAI Codex (v1.5)
- Claude Code (Haiku v3)

## 로컬 실행 방법

```bash
# 의존성 설치
poetry install

# 가상환경 활성화
poetry shell

# 서버 실행
uvicorn codereview_agent.app.run:codeReviewAgent --reload
```

## 디렉토리 구조

```
codereview_agent/
├── app/                     # FastAPI 앱 구동 관련 파일
│   ├── main.py              # FastAPI 라우터 등록
│   └── run.py               # PyCharm 실행용 진입점
│
├── review/                  # 코드 리뷰 도메인
│   ├── api/                 # API 핸들러
│   ├── models/              # Pydantic 모델 정의
│   ├── service/             # 비즈니스 로직 처리
│   └── __init__.py

```

## 주요 API 예시

### POST - `/api/reviews`

```json
Request:
{
  "code": "function sum(a,b){ return a+b; }",
  "language": "javascript",
  "style": "bug"
}
```

```json
Response:
{
  "code": 200,
  "message": "OK",
  "data": {
    "sessionId": "abc-123",
    "originalCode": "...",
    "currentCode": "...",
    "summary": "...",
    "suggestions": [...]
  }
}
```

## Swagger 문서

`http://localhost:8000/docs`
