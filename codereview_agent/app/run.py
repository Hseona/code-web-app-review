# run.py
import uvicorn
from codereview_agent.app.main import codeReviewAgent

if __name__ == "__main__":
    uvicorn.run(codeReviewAgent, host="127.0.0.1", port=8000, reload=True)