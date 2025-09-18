from fastapi import APIRouter

from codereview_agent.review.models.ReviewRequest import ReviewRequest

router = APIRouter()

# POST /api/reviews
@router.post("/reviews")
async def request_code_review(request: ReviewRequest):
    # TODO: 리뷰 비즈니스 로직 연결 예정
    return {"message": "Review request received"}