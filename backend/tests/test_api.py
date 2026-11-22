"""Unit tests for the FastAPI job routes."""

import asyncio

import pytest
from fastapi import HTTPException
from src import api
from src.models import JobCreateRequest


@pytest.fixture
def mocked_storage(monkeypatch):
    calls: dict[str, object] = {"statuses": []}

    async def send_job(job_id: str, url: str) -> int:
        calls["send"] = (job_id, url)
        return 1

    async def set_job_status(job_id: str, status: str, error: str | None = None) -> None:
        statuses = calls["statuses"]
        assert isinstance(statuses, list)
        statuses.append((job_id, status, error))

    async def get_job_status(job_id: str) -> dict | None:
        if job_id == "missing":
            return None
        status = "running" if job_id == "running" else "done"
        return {
            "id": job_id,
            "status": status,
            "error": None,
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        }

    async def get_job_result(job_id: str) -> dict | None:
        if job_id == "no-result":
            return None
        return {"quotes": [{"text": "Hello", "author": "World", "tags": []}]}

    monkeypatch.setattr(api.queue, "send_job", send_job)
    monkeypatch.setattr(api.db, "set_job_status", set_job_status)
    monkeypatch.setattr(api.db, "get_job_status", get_job_status)
    monkeypatch.setattr(api.db, "get_job_result", get_job_result)
    return calls


def test_create_job_enqueues_and_sets_status(mocked_storage):
    response = asyncio.run(
        api.create_job(JobCreateRequest(url="https://example.com"))
    )

    assert response.status == "queued"
    assert response.job_id
    assert mocked_storage["send"] == (response.job_id, "https://example.com")
    assert mocked_storage["statuses"] == [(response.job_id, "queued", None)]


def test_get_job_returns_status(mocked_storage):
    response = asyncio.run(api.get_job("running"))

    assert response.id == "running"
    assert response.status == "running"


def test_get_job_returns_404(mocked_storage):
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(api.get_job("missing"))

    assert exc_info.value.status_code == 404


def test_get_job_result_returns_payload(mocked_storage):
    result = asyncio.run(api.get_job_result("done"))

    assert result["quotes"][0]["text"] == "Hello"


@pytest.mark.parametrize("job_id", ["missing", "running", "no-result"])
def test_get_job_result_returns_404(mocked_storage, job_id):
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(api.get_job_result(job_id))

    assert exc_info.value.status_code == 404


def test_health_requires_secret(mocked_storage, monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(
        api, "get_settings", lambda: SimpleNamespace(internal_secret="secret")
    )

    assert asyncio.run(api.health("Bearer secret")) == {"status": "ok"}

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(api.health("Bearer wrong"))

    assert exc_info.value.status_code == 401
