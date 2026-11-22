"""Supabase Postgres access layer for job statuses and results.

`supabase-py` exposes a synchronous client, so every network call is executed
in a worker thread to keep the FastAPI event loop responsive.
"""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from supabase import Client, create_client

from .config import get_settings

logger = logging.getLogger(__name__)

JOB_STATUS_COLUMNS = "id,status,error,created_at,updated_at"

_client: Client | None = None

def get_client() -> Client:
    """Return a lazily created Supabase client."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = create_client(settings.supabase_url, settings.supabase_anon_key)
    return _client


async def _run(func: Any) -> Any:
    """Execute a synchronous supabase-py call in a worker thread."""
    return await asyncio.to_thread(func)

async def init_db() -> None:
    """Tables are pre-created via setup_supabase.sql. No runtime check needed."""
    logger.info("Database initialization skipped (tables verified manually)")

async def set_job_status(job_id: str, status: str, error: str | None = None) -> None:
    """Create or update a job status row."""
    client = get_client()
    payload = {
        "id": job_id,
        "status": status,
        "error": error,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    await _run(
        lambda: client.table("job_status").upsert(payload, on_conflict="id").execute()
    )


async def get_job_status(job_id: str) -> dict | None:
    """Return a job status row or `None` when the job does not exist."""
    client = get_client()
    response = await _run(
        lambda: client.table("job_status")
        .select(JOB_STATUS_COLUMNS)
        .eq("id", job_id)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else None


async def save_job_result(job_id: str, result: dict) -> None:
    """Persist the scraping result for a job (idempotent on `job_id`)."""
    client = get_client()
    payload = {"id": job_id, "result": result}
    await _run(
        lambda: client.table("job_results").upsert(payload, on_conflict="id").execute()
    )


async def get_job_result(job_id: str) -> dict | None:
    """Return the stored result payload or `None` when it is missing."""
    client = get_client()
    response = await _run(
        lambda: client.table("job_results")
        .select("result")
        .eq("id", job_id)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0]["result"] if rows else None
