"""Supabase pgmq queue wrapper using direct HTTP requests to public schema."""

import logging
from typing import Any

import httpx

from .config import QUEUE_NAME, get_settings

logger = logging.getLogger(__name__)


async def _call_pgmq_rpc(function_name: str, params: dict) -> Any:
    """Call a pgmq wrapper function in the public schema via direct HTTP."""
    settings = get_settings()
    
    base_url = settings.supabase_url.rstrip("/")
    rpc_url = f"{base_url}/rest/v1/rpc/{function_name}"
    
    headers = {
        "apikey": settings.supabase_anon_key,
        "Authorization": f"Bearer {settings.supabase_anon_key}",
        "Content-Type": "application/json",
    }
    
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        response = await http_client.post(rpc_url, json=params, headers=headers)
        
    if response.status_code != 200:
        logger.error(f"RPC {function_name} failed: {response.status_code} - {response.text}")
        raise RuntimeError(f"Queue RPC error: {response.text}")
        
    return response.json()


async def send_job(job_id: str, url: str) -> Any:
    """Enqueue a scraping job."""
    return await _call_pgmq_rpc(
        "pgmq_send", 
        {"queue_name": QUEUE_NAME, "message": {"job_id": job_id, "url": url}},
    )


async def read_job(vt: int = 30) -> dict | None:
    """Read a single job from the queue."""
    data = await _call_pgmq_rpc(
        "pgmq_read",
        {"queue_name": QUEUE_NAME, "vt": vt, "qty": 1},
    )
    
    if not data:
        return None
        
    messages = data if isinstance(data, list) else [data]
    return messages[0] if messages else None


async def archive_job(msg_id: int) -> Any:
    """Archive a processed message."""
    return await _call_pgmq_rpc(
        "pgmq_archive",
        {"queue_name": QUEUE_NAME, "msg_id": msg_id},
    )


async def init_queue() -> None:
    """Log hint about manual setup."""
    logger.info("Using pgmq wrappers in public schema")
