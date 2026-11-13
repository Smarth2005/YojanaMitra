"""FastAPI service for YojanaMitra."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
from prometheus_client import Counter, Histogram, generate_latest
from pydantic import BaseModel, Field

from .rag import RAGPipeline
from .retriever import Retriever

REQUESTS = Counter("yojanamitra_requests_total", "API requests")
REQUEST_LATENCY = Histogram("yojanamitra_request_latency_seconds", "Request latency")
RETRIEVAL_LATENCY = Histogram("yojanamitra_retrieval_latency_seconds", "Retrieval latency")
LLM_ERRORS = Counter("yojanamitra_llm_errors_total", "LLM errors")
NO_ANSWER = Counter("yojanamitra_no_answer_total", "Answers without retrieved context")


class Profile(BaseModel):
    age: int | None = Field(default=None, ge=0, le=120)
    state: str | None = None
    occupation: str | None = None
    gender: str | None = None


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    profile: Profile | None = None


class Source(BaseModel):
    scheme_name: str
    section: str
    text: str
    source_url: str = ""


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]
    query_type: str
    latency_ms: float


def create_app(pipeline: RAGPipeline | None = None) -> FastAPI:
    app = FastAPI(title="YojanaMitra API", version="1.0.0")
    if pipeline is None:
        class LazyPipeline:
            _pipeline: RAGPipeline | None = None

            def answer(self, question: str, profile: dict[str, Any] | None = None) -> Any:
                if self._pipeline is None:
                    self._pipeline = RAGPipeline(Retriever())
                return self._pipeline.answer(question, profile)

        pipeline = LazyPipeline()
    windows: dict[str, deque[float]] = defaultdict(deque)

    @app.middleware("http")
    async def rate_limit(request: Request, call_next: Any) -> Any:
        if request.url.path == "/api/ask":
            now = time.time()
            client = request.client.host if request.client else "unknown"
            queue = windows[client]
            while queue and queue[0] < now - 60:
                queue.popleft()
            from .config import API_RATE_LIMIT
            if len(queue) >= API_RATE_LIMIT:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            queue.append(now)
        return await call_next(request)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/metrics", response_class=PlainTextResponse)
    def metrics() -> PlainTextResponse:
        return PlainTextResponse(generate_latest().decode(), media_type="text/plain")

    @app.post("/api/ask", response_model=AskResponse)
    def ask(payload: AskRequest) -> AskResponse:
        started = time.perf_counter()
        REQUESTS.inc()
        try:
            result = pipeline.answer(
                payload.question,
                payload.profile.model_dump(exclude_none=True) if payload.profile else None,
            )
        except Exception as exc:
            LLM_ERRORS.inc()
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        if not result.sources:
            NO_ANSWER.inc()
        latency = (time.perf_counter() - started) * 1000
        REQUEST_LATENCY.observe(latency / 1000)
        sources = [
            Source(
                scheme_name=chunk.metadata.get("scheme_name", ""),
                section=chunk.metadata.get("section", ""),
                text=chunk.text,
                source_url=chunk.metadata.get("source_url", ""),
            )
            for chunk in result.sources
        ]
        return AskResponse(
            answer=result.answer,
            sources=sources,
            query_type=result.query_type,
            latency_ms=round(latency, 2),
        )

    return app


app = create_app()
