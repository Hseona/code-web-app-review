"""Example instances for review response models."""

EXAMPLE_REVIEW_RESPONSE = {
    "code": 200,
    "message": "OK",
    "data": {
        "session_id": "abc-123",
        "original_code": "function sum(a,b){ return a+b }",
        "current_code": "function sum(a,b){ return a+b }",
        "summary": "가독성 개선 제안이 있습니다",
        "suggestions": [
            {
                "id": "uuid",
                "title": "함수 네이밍 개선",
                "rationale": "명확한 함수명을 권장합니다",
                "severity": "minor",
                "tags": ["readability"],
                "range": {
                    "start_line": 1,
                    "start_col": 10,
                    "end_line": 1,
                    "end_col": 13
                },
                "fix": {
                    "type": "unified-diff",
                    "diff": "--- a\n+++ b\n@@ -1 +1 @@\n-function sum\n+function calculateSum"
                },
                "fix_snippet": "function calculateSum(a, b) { return a + b; }",
                "confidence": 0.91,
                "status": "pending"
            }
        ],
        "metrics": {
            "processing_time_ms": 8132,
            "model": "claude-3-haiku"
        }
    }
}