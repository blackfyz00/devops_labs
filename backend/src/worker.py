"""Asyncio worker loop that consumes jobs from the queue."""

import asyncio
import json
import logging

from . import db, queue, scraper
from .config import JOB_TIMEOUT_SECONDS, WORKER_POLL_INTERVAL

logger = logging.getLogger(__name__)


def _parse_payload(message: dict) -> dict | None:
    """Extract the job payload from a pgmq message."""
    payload = message.get("message", {})
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            logger.error("Message contains invalid JSON: %s", message)
            return None

    if (
        not isinstance(payload, dict)
        or not payload.get("job_id")
        or not payload.get("url")
    ):
        logger.error("Message has no job_id/url: %s", message)
        return None

    return payload


async def _process_message(message: dict) -> None:
    """Process a single queue message and archive it afterwards."""
    msg_id = message["msg_id"]
    payload = _parse_payload(message)

    if payload is None:
        await queue.archive_job(msg_id)
        return

    job_id = payload["job_id"]
    url = payload["url"]
    logger.info("Processing job %s for URL: %s", job_id, url)

    await db.set_job_status(job_id, "running")

    try:
        result = await asyncio.wait_for(
            scraper.scrape_url(url), timeout=JOB_TIMEOUT_SECONDS
        )
        await db.save_job_result(job_id, result.to_dict())
        await db.set_job_status(job_id, "done")
        logger.info("Job %s finished", job_id)
    except Exception as exc:
        error_message = str(exc) or type(exc).__name__
        logger.exception("Job %s failed: %s", job_id, error_message)
        await db.set_job_status(job_id, "failed", error=error_message)
    finally:
        await queue.archive_job(msg_id)


async def worker_loop() -> None:
    """Consume jobs from the queue until the task is cancelled."""
    logger.info("Worker started")

    while True:
        try:
            message = await queue.read_job(vt=30)
            if message is not None:
                await _process_message(message)
        except asyncio.CancelledError:
            logger.info("Worker stopped")
            raise
        except Exception:
            logger.exception("Critical error in worker loop")

        await asyncio.sleep(WORKER_POLL_INTERVAL)
