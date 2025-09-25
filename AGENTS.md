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
  - 원격 호출이 실패하면 공통 메시지 템플릿으로 휴리스틱 요약을 작성한 뒤 `CustomInternalServerException(ErrorCode.SERVICE_UNAVAILABLE)`을 발생시켜 503 오류 응답으로 전달합니다.

## 2. 에이전트 동작 방식
- 입력 구조:
  - `code`: 리뷰 대상 코드 문자열 (필수)
  - `language`: 언어 명시 (선택, 공백이면 무시)
  - `style`: 리뷰 스타일 프로필 (`bug` | `detail` | `refactor` | `test`)
- 처리 로직:
  - 요청이 유효하면 `ApiSuccessResponse.code` 200과 함께 Claude 응답 또는 휴리스틱 요약을 포함한 데이터를 반환합니다.
  - Claude 호출 도중 예외가 발생하면 도메인 예외(`CustomInternalServerException` 등)를 발생시키고, 전역 예외 핸들러가 `ApiErrorResponse`(503)에 휴리스틱 요약과 사유를 담아 전달합니다.

## 3. API 입력 및 출력 구조
- 성공 구조 (`ApiSuccessResponse`):
  - `code`: HTTP 상태 코드 값 (예: 200)
  - `message`: 처리 결과 메시지 (`"OK"` 등)
  - `data`: 객체 또는 리스트 형태의 결과 컨테이너
    - 객체(`dict`)일 경우: `sessionId`, `originalCode`, `currentCode`, `summary`, `suggestions`, `metrics`
    - 리스트(`list`)일 경우: 제안 배열/히스토리 목록 등 비어 있거나 다수의 엔트리를 포함
- 실패 구조 (`ApiErrorResponse`):
  - `status`: 오류 유형 문자열 (예: `"BAD_REQUEST"`, `"SERVICE_UNAVAILABLE"`)
  - `code`: HTTP 상태 코드 값 (예: 400, 503)
  - `message`: 사용자 대상 오류 설명 (휴리스틱 요약 포함 가능)
  - `errors`: 필드 단위 오류 목록 (`field`, `message` 포함)

### 성공 응답 예시

```json
// object
{
  "code": 200,
  "message": "OK",
  "data": {}
}

// list
{
  "code": 200,
  "message": "OK",
  "data": []
}
```

### 실패 응답 예시

```json
{
  "status": "BAD_REQUEST",
  "code": 400,
  "message": "필수값이 누락 되었거나 요청 형식이 유효하지 않습니다.",
  "errors": [
    {
      "field": "userId",
      "message": "userId는 필수값입니다."
    }
  ]
}
```

## 4. Fallback 및 예외 처리
- 백업 휴리스틱 제안(오류 메시지와 내부 가이드에 활용):
  - `==`를 `===`로 치환하는 동등 연산자 강화
  - `console.log`를 주석 안내로 교체해 릴리스 시 로그를 정리하도록 권장
  - 설명이 없는 `TODO`에 세부 설명 추가 권장
  - 테스트 스타일 요청인데 테스트 코드 흔적이 없을 때 테스트 스캐폴드 추가 권장
- 추가 메모:
  - 모든 원격 제안은 누락된 필드가 있으면 자동으로 채워집니다.
  - 오류 응답은 `ApiErrorResponse` 구조만 반환하며 메트릭은 성공 응답에서만 제공됩니다.
  - 사용자 노출 메시지는 `codereview_agent.common.messages`에 정의된 템플릿을 사용해 하드코딩을 지양합니다.
  - 언어를 명시하지 않으면 자바스크립트를 기본값으로 사용합니다.

## 5. 개발 컨벤션

- **클래스/함수 명명**: 파이썬 PEP8 규칙에 따라 PascalCase(클래스), snake_case(함수) 사용
- **파일명/모듈 구조**: snake_case 사용. 모든 리뷰 관련 로직은 `codereview_agent/review/` 내에 위치
- **테스트**: pytest 기반. 모든 테스트는 `tests/` 디렉터리에 위치
- **타입 힌트**: 모든 함수에 타입 힌트를 작성하며, 테스트 코드에도 작성 권장
- **형식 검사 도구**: black + mypy + ruff 적용
- **환경 변수 관리**: `.env` 파일을 사용하며, `ClaudeSettings`를 통해 불러옴. 민감 정보는 Git에 커밋하지 않음
- **하드코딩 지양**: 사용자 노출 메시지나 비즈니스 상수는 공통 모듈/설정에서 관리하고, 서비스 로직에서는 해당 상수를 참조만 합니다.

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
- Claude 호출 실패 시: `ErrorCode.SERVICE_UNAVAILABLE` 오류 응답과 휴리스틱 요약을 반환
