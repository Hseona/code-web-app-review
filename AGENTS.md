# AGENTS.md

## 목차

1. [개요 및 역할](#1-개요-및-역할)  
2. [에이전트 동작 방식](#2-에이전트-동작-방식)  
3. [API 입력 및 출력 구조](#3-api-입력-및-출력-구조)  
4. [Fallback 및 예외 처리](#4-fallback-및-예외-처리)  
5. [개발 컨벤션](#5-개발-컨벤션)  
   - [5.1 커밋 메시지 규칙](#51-커밋-메시지-규칙)  
   - [5.2 브랜치 전략](#52-브랜치-전략)  
6. [AI/모델 설정](#6-ai모델-설정)

## 1. 개요 및 역할
- 목적: 사용자의 코드와 선택한 리뷰 스타일을 기반으로 구조화된 리뷰 결과와 패치를 생성합니다.
- 핵심 동작:
  - FastAPI `/api/reviews` 엔드포인트가 요청 본문을 수신하면 개행/따옴표가 이스케이프되지 않은 JSON도 정규화해 `ReviewRequest` 스키마로 검증합니다.
  - `ReviewService`가 스타일을 소문자화하고 기본값 `detail`을 적용하며 TypeScript 신호(`interface`, `: number` 등)를 우선 검사해 언어를 추론합니다.
  - 모델 입력 길이를 500자로 제한한 뒤 `ClaudeReviewClient`가 Claude 3 Haiku Messages API를 최대 3회까지 재시도하면서 호출합니다.
  - Claude 응답에서 제안·요약·메트릭을 정규화하고 누락된 `id`/`status` 필드를 보완하며, 요약이 비어 있으면 스타일 프로필을 기반으로 생성합니다.
  - 원격 호출이 실패하면 사유를 담은 요약과 함께 휴리스틱 제안들을 제공하고, 메트릭의 모델명을 `codex-heuristic-v1`로 설정합니다.

## 2. 에이전트 동작 방식
- 입력 구조:
  - `code`: 리뷰 대상 코드 문자열 (필수)
  - `language`: 언어 명시 (선택, 공백이면 무시)
  - `style`: 리뷰 스타일 프로필 (`bug` | `detail` | `refactor` | `test`)
- 처리 로직:
  - 요청이 유효하면 `ReviewResponse.code` 200과 함께 Claude 응답 또는 휴리스틱 결과를 반환합니다.
  - Claude 호출 도중 예외가 발생하면 503과 함께 휴리스틱 제안을 포함한 응답을 반환합니다.

## 3. API 입력 및 출력 구조
- 출력 구조 (`ReviewResponse`):
  - `code`: HTTP 상태 코드 값 (예: 200, 503)
  - `message`: 처리 결과 메시지 (`"OK"`, `"Claude API 호출 실패"` 등)
  - `data`: 리뷰 결과
    - `sessionId`: 리뷰 세션 고유 ID (UUID)
    - `originalCode`: 입력 코드 원문
    - `currentCode`: 제안 적용 전 코드 (초기에는 원문과 동일)
    - `summary`: 스타일 프로필과 언어 관점의 리뷰 요약 (Claude 응답 또는 자동 생성)
    - `suggestions`: 제안 리스트
      - `id`, `title`, `rationale`, `severity`, `tags`
      - `range`: `startLine`, `startCol`, `endLine`, `endCol`
      - `fix`: `type`(예: `unified-diff`), `diff`
      - `fixSnippet`: 적용 결과 스니펫
      - `confidence`: 0~1 사이 신뢰도
      - `status`: `pending` | `accepted` | `rejected`
    - `metrics`: `processingTimeMs`(원격 응답값 또는 처리 시간), `model`(원격 성공 시 Claude 모델명, 실패 시 `codex-heuristic-v1`)

## 4. Fallback 및 예외 처리
- 백업 휴리스틱 제안:
  - `==`를 `===`로 치환하는 동등 연산자 강화
  - `console.log`를 주석 안내로 교체해 릴리스 시 로그를 정리하도록 권장
  - 설명이 없는 `TODO`에 세부 설명 추가 권장
  - 테스트 스타일 요청인데 테스트 코드 흔적이 없을 때 테스트 스캐폴드 추가 권장
- 추가 메모:
  - 모든 원격 제안은 누락된 필드가 있으면 자동으로 채워집니다.
  - 처리 시간은 Claude 응답 메트릭이 없을 경우 서비스 레벨에서 측정한 시간을 사용합니다.
  - 언어를 명시하지 않으면 자바스크립트를 기본값으로 사용합니다.

## 5. 개발 컨벤션

- **클래스/함수 명명**: 파이썬 PEP8 규칙에 따라 PascalCase(클래스), snake_case(함수) 사용
- **파일명/모듈 구조**: snake_case 사용. 모든 리뷰 관련 로직은 `codereview_agent/review/` 내에 위치
- **테스트**: pytest 기반. 모든 테스트는 `tests/` 디렉터리에 위치
- **타입 힌트**: 모든 함수에 타입 힌트를 작성하며, 테스트 코드에도 작성 권장
- **형식 검사 도구**: black + mypy + ruff 적용
- **환경 변수 관리**: `.env` 파일을 사용하며, `ClaudeSettings`를 통해 불러옴. 민감 정보는 Git에 커밋하지 않음

### 5.1 커밋 메시지 규칙

- `feature:` 새로운 기능 추가  
- `fix:` 버그 수정  
- `test:` 테스트 코드 추가  
- `refactor:` 리팩토링  
- `chore:` 설정/기타 파일 관련 수정  
- `docs:` 문서 관련 수정  

### 5.2 브랜치 전략

- Git Flow 준수
- 모든 PR은 최소 1인 이상의 코드 리뷰 후 `develop` 병합
- 배포 전까지는 `master`에 병합

## 6. AI/모델 설정

- 기본 리뷰 모델: `claude-3-haiku-20240307`
- 코드 길이 500자 이상일 경우 자동 truncate
- Claude 호출 실패 시: fallback 모델 `codex-heuristic-v1` 사용