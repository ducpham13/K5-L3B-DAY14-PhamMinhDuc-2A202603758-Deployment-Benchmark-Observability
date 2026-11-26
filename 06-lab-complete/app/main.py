"""
Production AI Agent — Part 6 Final Project
"""
import json
import logging
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, Response
from pydantic import BaseModel, Field

from app.auth import verify_api_key
from app.cost_guard import check_budget, record_cost
from app.rate_limiter import check_rate_limit
from app.redis_client import redis_healthy
from utils.mock_llm import ask as llm_ask


# --- Structured JSON logging ---
class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "lvl": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload)


_handler = logging.StreamHandler()
_handler.setFormatter(_JsonFormatter())
logging.root.handlers = [_handler]
logging.root.setLevel(logging.INFO)
logger = logging.getLogger(__name__)


# --- Lifespan (graceful shutdown handled by uvicorn on SIGTERM) ---
@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Agent starting up")
    yield
    logger.info("Agent shut down")


app = FastAPI(title="Production AI Agent", lifespan=lifespan)


# --- Health / readiness ---
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    if redis_healthy():
        return {"status": "ready"}
    return Response(
        content=json.dumps({"status": "not ready", "reason": "redis unavailable"}),
        status_code=503,
        media_type="application/json",
    )


# --- Main endpoint ---
class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    user_id: str | None = None


@app.post("/ask")
def ask(body: AskRequest, _request: Request, api_key: str = Depends(verify_api_key)):
    check_rate_limit(api_key)
    check_budget()

    t0 = time.time()
    answer = llm_ask(body.question)
    elapsed_ms = (time.time() - t0) * 1000

    input_tokens = len(body.question.split())
    output_tokens = len(answer.split())
    cost = record_cost(input_tokens, output_tokens)

    logger.info("path=/ask status=200 ms=%.1f cost_usd=%.6f", elapsed_ms, cost)

    return {"question": body.question, "answer": answer}
