"""Business logic for handling code review requests."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Iterable, List, Optional
from uuid import uuid4

from pydantic import ValidationError

from codereview_agent.review.models import (
    ReviewData,
    ReviewMetrics,
    Suggestion,
    SuggestionFix,
    SuggestionRange,
)
from codereview_agent.review.schemas import ReviewRequest, ReviewResponse
from codereview_agent.review.service.claude_client import (
    ClaudeReviewClient,
    ClaudeReviewError,
)


@dataclass(frozen=True)
class StyleProfile:
    key: str
    summary_label: str
    description: str


STYLE_PROFILES = {
    "bug": StyleProfile(
        key="bug",
        summary_label="버그 중심",
        description="명확한 오류나 잠재적 버그를 우선적으로 탐지합니다.",
    ),
    "detail": StyleProfile(
        key="detail",
        summary_label="디테일 중심",
        description="가독성과 일관성을 개선할 수 있는 제안을 제공합니다.",
    ),
    "refactor": StyleProfile(
        key="refactor",
        summary_label="리팩터링 중심",
        description="구조 개선과 클린 코드 관점을 강조합니다.",
    ),
    "test": StyleProfile(
        key="test",
        summary_label="테스트 중심",
        description="테스트 보강과 품질 확보에 초점을 둡니다.",
    ),
}

DEFAULT_STYLE = "detail"
DEFAULT_LANGUAGE = "javascript"
FALLBACK_MODEL_NAME = "codex-heuristic-v1"


class ReviewService:
    """Generates structured code review results via Claude integration with fallback heuristics."""

    def __init__(self, review_client: Optional[ClaudeReviewClient] = None) -> None:
        self._review_client = review_client

    def generate_review(self, request: ReviewRequest) -> ReviewResponse:
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
            return ReviewResponse(code=200, message="OK", data=data)
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

            return ReviewResponse(
                code=503,
                message="Claude API 호출 실패",
                data=data,
            )

    # --- helpers -----------------------------------------------------------------

    def _build_remote_data(
        self,
        *,
        request: ReviewRequest,
        style: str,
        language: str,
        remote_payload: dict,
        client: ClaudeReviewClient,
        started_at: float,
    ) -> ReviewData:
        remote_suggestions = remote_payload.get("suggestions")
        suggestions = self._normalize_remote_suggestions(remote_suggestions)

        summary = remote_payload.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            summary = self._build_summary(style, language, suggestions)

        metrics_payload = remote_payload.get("metrics") if isinstance(remote_payload, dict) else None

        processing_ms: Optional[int] = None
        model_name: Optional[str] = None

        if isinstance(metrics_payload, dict):
            processing_candidate = metrics_payload.get("processingTimeMs")
            if isinstance(processing_candidate, int) and processing_candidate >= 0:
                processing_ms = processing_candidate

            model_candidate = metrics_payload.get("model")
            if isinstance(model_candidate, str) and model_candidate.strip():
                model_name = model_candidate

        if processing_ms is None:
            processing_ms = int((time.perf_counter() - started_at) * 1000)

        if not model_name:
            model_name = client.model_name

        return ReviewData(
            session_id=str(uuid4()),
            original_code=request.code,
            current_code=request.code,
            summary=summary,
            suggestions=suggestions,
            metrics=ReviewMetrics(
                processing_time_ms=processing_ms,
                model=model_name,
            ),
        )

    def _normalize_remote_suggestions(self, raw_suggestions: Any) -> List[Suggestion]:
        if not isinstance(raw_suggestions, Iterable):
            return []

        suggestions: List[Suggestion] = []
        for entry in raw_suggestions:
            if not isinstance(entry, dict):
                continue

            normalized = dict(entry)
            normalized.setdefault("id", str(uuid4()))
            normalized.setdefault("status", "pending")

            try:
                suggestion = Suggestion.model_validate(normalized)
            except ValidationError:
                continue

            suggestions.append(suggestion)

        return suggestions

    def _normalize_style(self, style: Optional[str]) -> str:
        if not style:
            return DEFAULT_STYLE
        normalized = style.lower()
        return normalized if normalized in STYLE_PROFILES else DEFAULT_STYLE

    def _resolve_language(self, language: Optional[str], code: str) -> str:
        if language:
            return language.lower()

        # Very light-weight heuristic favouring TypeScript patterns first.
        ts_signals = ["interface ", "type ", ": number", ": string", "enum ", "<T>"]
        if any(signal in code for signal in ts_signals):
            return "typescript"

        js_signals = ["function ", "const ", "let ", "import ", "export "]
        if any(signal in code for signal in js_signals):
            return "javascript"

        return DEFAULT_LANGUAGE

    def _build_summary(self, style: str, language: str, suggestions: List[Suggestion]) -> str:
        profile = STYLE_PROFILES.get(style, STYLE_PROFILES[DEFAULT_STYLE])
        language_label = language.upper()
        if not suggestions:
            return (
                f"{language_label} 코드를 {profile.summary_label} 관점에서 검토했지만, "
                "즉시 적용할 개선점을 찾지 못했습니다."
            )
        return (
            f"{language_label} 코드를 {profile.summary_label} 관점에서 검토해 "
            f"{len(suggestions)}개의 제안을 생성했습니다."
        )

    def _collect_suggestions(self, code: str, style: str) -> List[Suggestion]:
        builders: List[Iterable[Suggestion]] = []
        if style in {"bug", "detail"}:
            builders.append(self._find_non_strict_equality(code))
        if style in {"bug", "refactor", "detail"}:
            builders.append(self._find_console_logs(code))
        if style in {"detail", "refactor"}:
            builders.append(self._find_sparse_todos(code))
        if style in {"test"}:
            builders.append(self._propose_test_scaffold(code))

        suggestions: List[Suggestion] = []
        for iterable in builders:
            suggestions.extend(iterable)
        return suggestions

    def _find_non_strict_equality(self, code: str) -> Iterable[Suggestion]:
        suggestions: List[Suggestion] = []
        for idx, line in enumerate(code.splitlines(), start=1):
            if "==" not in line or "===" in line or "!==" in line:
                continue
            col = line.index("==") + 1
            new_line = line.replace("==", "===", 1)
            diff = "\n".join(
                [
                    "--- original",
                    "+++ updated",
                    f"@@ -{idx} +{idx} @@",
                    f"-{line}",
                    f"+{new_line}",
                ]
            )
            suggestions.append(
                Suggestion(
                    id=str(uuid4()),
                    title="동등 연산자 강화",
                    rationale="JavaScript에서는 엄격한 비교(===)가 암묵적 형 변환으로 인한 버그를 예방합니다.",
                    severity="major",
                    tags=["bug", "best-practice"],
                    range=SuggestionRange(
                        start_line=idx,
                        start_col=col,
                        end_line=idx,
                        end_col=col + 2,
                    ),
                    fix=SuggestionFix(type="unified-diff", diff=diff),
                    fix_snippet=new_line.strip(),
                    confidence=0.7,
                    status="pending",
                )
            )
        return suggestions

    def _find_console_logs(self, code: str) -> Iterable[Suggestion]:
        suggestions: List[Suggestion] = []
        for idx, line in enumerate(code.splitlines(), start=1):
            if "console.log" not in line:
                continue
            stripped = line.rstrip("\n")
            indent = len(stripped) - len(stripped.lstrip(" "))
            replacement = " " * indent + "// TODO: 필요한 경우 로깅 가드를 적용하세요."
            diff = "\n".join(
                [
                    "--- original",
                    "+++ updated",
                    f"@@ -{idx} +{idx} @@",
                    f"-{stripped}",
                    f"+{replacement}",
                ]
            )
            suggestions.append(
                Suggestion(
                    id=str(uuid4()),
                    title="디버그 로그 정리",
                    rationale="프로덕션 코드에서는 console.log를 제거하거나 환경에 따라 제어하는 것이 좋습니다.",
                    severity="minor",
                    tags=["cleanup", "refactor"],
                    range=SuggestionRange(
                        start_line=idx,
                        start_col=stripped.index("console.log") + 1,
                        end_line=idx,
                        end_col=stripped.index("console.log") + len("console.log") + 1,
                    ),
                    fix=SuggestionFix(type="unified-diff", diff=diff),
                    fix_snippet=replacement.strip(),
                    confidence=0.6,
                    status="pending",
                )
            )
        return suggestions

    def _find_sparse_todos(self, code: str) -> Iterable[Suggestion]:
        suggestions: List[Suggestion] = []
        for idx, line in enumerate(code.splitlines(), start=1):
            if "TODO" not in line:
                continue
            if ":" in line:
                # Already has a description.
                continue
            stripped = line.rstrip("\n")
            placeholder = stripped.replace("TODO", "TODO: 세부 설명을 추가하세요")
            diff = "\n".join(
                [
                    "--- original",
                    "+++ updated",
                    f"@@ -{idx} +{idx} @@",
                    f"-{stripped}",
                    f"+{placeholder}",
                ]
            )
            suggestions.append(
                Suggestion(
                    id=str(uuid4()),
                    title="TODO 세부 설명 추가",
                    rationale="TODO에는 구체적인 작업 내용을 작성해야 추후 처리하기 쉽습니다.",
                    severity="minor",
                    tags=["documentation", "detail"],
                    range=SuggestionRange(
                        start_line=idx,
                        start_col=stripped.index("TODO") + 1,
                        end_line=idx,
                        end_col=stripped.index("TODO") + len("TODO") + 1,
                    ),
                    fix=SuggestionFix(type="unified-diff", diff=diff),
                    fix_snippet=placeholder.strip(),
                    confidence=0.5,
                    status="pending",
                )
            )
        return suggestions

    def _propose_test_scaffold(self, code: str) -> Iterable[Suggestion]:
        lowered = code.lower()
        has_test_keyword = any(
            keyword in lowered for keyword in ("test(", "it(", "describe(", "expect(", "assert(")
        )
        if has_test_keyword:
            return []

        snippet = (
            "describe('module', () => {\n"
            "  it('should do something meaningful', () => {\n"
            "    // TODO: add assertions matching the new behaviour\n"
            "  });\n"
            "});"
        )
        total_lines = code.count("\n") + 1
        diff_lines = [
            "--- original",
            "+++ updated",
            f"@@ +{total_lines + 1},{4} @@",
        ] + [f"+{line}" for line in snippet.splitlines()]
        diff = "\n".join(diff_lines)

        suggestion = Suggestion(
            id=str(uuid4()),
            title="테스트 스캐폴드 추가",
            rationale="새로운 변경 사항이 테스트로 검증되면 회귀를 예방할 수 있습니다.",
            severity="major",
            tags=["test", "quality"],
            range=SuggestionRange(
                start_line=total_lines,
                start_col=1,
                end_line=total_lines,
                end_col=1,
            ),
            fix=SuggestionFix(type="unified-diff", diff=diff),
            fix_snippet=snippet,
            confidence=0.4,
            status="pending",
        )
        return [suggestion]
