"""Primary payload model for code review responses."""

from pydantic import BaseModel, ConfigDict, Field
from codereview_agent.review.models.review_metrics import ReviewMetrics
from codereview_agent.review.models.suggestion import Suggestion

class ReviewData(BaseModel):
    session_id: str = Field(alias="sessionId")
    original_code: str = Field(alias="originalCode")
    current_code: str = Field(alias="currentCode")
    summary: str
    suggestions: list[Suggestion]
    metrics: ReviewMetrics

    model_config = ConfigDict(populate_by_name=True)
