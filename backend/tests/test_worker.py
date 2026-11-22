"""Unit tests for the queue worker."""

import asyncio
from types import SimpleNamespace

from src import worker


def _patch_worker(monkeypatch, scrape):
    calls: list[tuple] = []

    async def set_job_status(job_id, status, error=None):
        calls.append(("status", job_id, status, error))

    async def save_job_result(job_id, result):
        calls.append(("result", job_id, result["total_count"]))

    async def archive_job(msg_id):
        calls.append(("archive", msg_id))

    async def read_job(vt=30):
        return None

    monkeypatch.setattr(worker.db, "set_job_status", set_job_status)
    monkeypatch.setattr(worker.db, "save_job_result", save_job_result)
    monkeypatch.setattr(worker.queue, "archive_job", archive_job)
    monkeypatch.setattr(worker.queue, "read_job", read_job)
    monkeypatch.setattr(worker.scraper, "scrape_url", scrape)
    return calls


async def _successful_scrape(url):
    return SimpleNamespace(to_dict=lambda: {"quotes": [], "total_count": 0})


def test_process_message_success(monkeypatch):
    calls = _patch_worker(monkeypatch, _successful_scrape)

    asyncio.run(
        worker._process_message(
            {"msg_id": 1, "message": {"job_id": "job-1", "url": "https://example.com"}}
        )
    )

    assert ("status", "job-1", "running", None) in calls
    assert ("result", "job-1", 0) in calls
    assert ("status", "job-1", "done", None) in calls
    assert calls[-1] == ("archive", 1)


def test_process_message_failure_marks_job_failed(monkeypatch):
    async def failing_scrape(url):
        raise RuntimeError("Browser quota exceeded")

    calls = _patch_worker(monkeypatch, failing_scrape)

    asyncio.run(
        worker._process_message(
            {"msg_id": 2, "message": '{"job_id": "job-2", "url": "https://example.com"}'}
        )
    )

    assert ("status", "job-2", "failed", "Browser quota exceeded") in calls
    assert calls[-1] == ("archive", 2)


def test_process_message_archives_invalid_payload(monkeypatch):
    calls = _patch_worker(monkeypatch, _successful_scrape)

    asyncio.run(worker._process_message({"msg_id": 3, "message": {"bad": True}}))

    assert calls == [("archive", 3)]
