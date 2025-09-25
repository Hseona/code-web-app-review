from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from codereview_agent.common import register_exception_handlers
from codereview_agent.review.api.review_router import router as review_router

codeReviewAgent = FastAPI()
register_exception_handlers(codeReviewAgent)

codeReviewAgent.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],

    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

codeReviewAgent.include_router(review_router, prefix="/api")
