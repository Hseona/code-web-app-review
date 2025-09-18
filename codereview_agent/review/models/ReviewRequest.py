# codereview_agent/review/models/review_request.py

from pydantic import BaseModel

class ReviewRequest(BaseModel):
    code: str
    language: str = "javascript"
    style: str