"""Top-level review response model."""

from pydantic import BaseModel, ConfigDict
from codereview_agent.review.models.review_data import ReviewData

class ReviewResponse(BaseModel):
    code: int
    message: str
    data: ReviewData

    model_config = ConfigDict(populate_by_name=True)
