from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from codereview_agent.review.api.router import router as review_router

codeReviewAgent = FastAPI()

codeReviewAgent.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],

    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

codeReviewAgent.include_router(review_router, prefix="/api")