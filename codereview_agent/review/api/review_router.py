from fastapi import APIRouter

from codereview_agent.review.schemas import ReviewRequest
from codereview_agent.review.service import ReviewService

router = APIRouter()
review_service = ReviewService()


@router.post("/reviews")
async def request_code_review(request: ReviewRequest):
    response = review_service.generate_review(request)
    return response.model_dump(by_alias=True)
