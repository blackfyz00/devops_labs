"""FastAPI application and job routes."""

import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import db, queue
from .config import get_settings
from .models import JobCreateRequest, JobResponse, JobStatusResponse
from .worker import worker_loop

logger = logging.getLogger(__name__)


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "http://localhost:5173")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize storage and queue, then run the background worker."""
    await db.init_db()
    await queue.init_queue()
    worker_task = asyncio.create_task(worker_loop())
    try:
        yield
    finally:
        worker_task.cancel()
        with suppress(asyncio.CancelledError):
            await worker_task


app = FastAPI(title="Quotes Scraper API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/jobs", status_code=202, response_model=JobResponse)
async def create_job(payload: JobCreateRequest) -> JobResponse:
    """Enqueue a scraping job and return its identifier."""
    job_id = str(uuid.uuid4())
    await queue.send_job(job_id, payload.url)
    await db.set_job_status(job_id, "queued")
    logger.info("Queued job %s for %s", job_id, payload.url)
    return JobResponse(job_id=job_id, status="queued")


@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: str) -> JobStatusResponse:
    """Return the current status of a job."""
    job_status = await db.get_job_status(job_id)
    if job_status is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse(**job_status)


@app.get("/jobs/{job_id}/result")
async def get_job_result(job_id: str) -> dict:
    """Return the scraping result once the job is done."""
    job_status = await db.get_job_status(job_id)
    if job_status is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job_status["status"] != "done":
        raise HTTPException(status_code=404, detail="Result is not available")

    result = await db.get_job_result(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Result is not available")
    return result


@app.get("/health")
async def health(authorization: str | None = Header(default=None)) -> dict[str, str]:
    """Keepalive endpoint protected by the shared internal secret."""
    expected = f"Bearer {get_settings().internal_secret}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"status": "ok"}


def run() -> None:
    """Run the API with uvicorn (used as the Render start command)."""
    import uvicorn

    uvicorn.run(
        "src.api:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
    )
