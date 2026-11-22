#!/usr/bin/env python3
"""End-to-end smoke test for the Quotes Scraper API.

Usage:
    python scripts/smoke_test.py [API_URL]
    API_URL=https://your-app.onrender.com python scripts/smoke_test.py
"""

import os
import sys
import time

import httpx

SCROLL_URL = "https://quotes.toscrape.com/scroll"
INVALID_URL = "https://invalid-domain-xyz.invalid"
DEFAULT_API_URL = "http://localhost:8000"
POLL_INTERVAL_SECONDS = 3.0
POLL_TIMEOUT_SECONDS = 120.0


class SmokeTestError(RuntimeError):
    """Raised when an end-to-end check fails."""


def _read_json(response: httpx.Response) -> dict:
    try:
        payload = response.json()
    except ValueError as exc:
        raise SmokeTestError(
            f"Expected JSON from {response.request.url}, got: {response.text[:300]!r}"
        ) from exc

    if not isinstance(payload, dict):
        raise SmokeTestError(
            f"Expected a JSON object from {response.request.url}, got: {payload!r}"
        )

    return payload


def _create_job(client: httpx.Client, api_url: str, url: str) -> str:
    response = client.post(f"{api_url}/jobs", json={"url": url})
    payload = _read_json(response)

    if response.status_code != 202:
        raise SmokeTestError(
            f"POST /jobs for {url} returned {response.status_code}: {payload}"
        )

    job_id = payload.get("job_id")
    if not isinstance(job_id, str) or not job_id:
        raise SmokeTestError(f"POST /jobs returned no job_id: {payload}")

    return job_id


def _wait_for_terminal_status(
    client: httpx.Client, api_url: str, job_id: str
) -> dict:
    deadline = time.monotonic() + POLL_TIMEOUT_SECONDS
    last_status: str | None = None

    while time.monotonic() < deadline:
        response = client.get(f"{api_url}/jobs/{job_id}")
        payload = _read_json(response)

        if response.status_code != 200:
            raise SmokeTestError(
                f"GET /jobs/{job_id} returned {response.status_code}: {payload}"
            )

        status = payload.get("status")
        if not isinstance(status, str):
            raise SmokeTestError(f"Job {job_id} returned no status: {payload}")

        if status != last_status:
            print(f"   status: {status}")
            last_status = status

        if status in {"done", "failed"}:
            return payload

        time.sleep(POLL_INTERVAL_SECONDS)

    raise SmokeTestError(
        f"Timed out after {POLL_TIMEOUT_SECONDS:.0f}s waiting for job {job_id} "
        f"(last status: {last_status})"
    )


def run(api_url: str) -> None:
    print(f"API: {api_url}")

    with httpx.Client(timeout=30.0) as client:
        print("[1/3] Scraping the known scroll page")
        job_id = _create_job(client, api_url, SCROLL_URL)
        print(f"   job_id: {job_id}")

        status_payload = _wait_for_terminal_status(client, api_url, job_id)
        if status_payload["status"] != "done":
            raise SmokeTestError(
                f"Job {job_id} failed: {status_payload.get('error') or 'unknown error'}"
            )

        response = client.get(f"{api_url}/jobs/{job_id}/result")
        result = _read_json(response)
        if response.status_code != 200:
            raise SmokeTestError(
                f"GET /jobs/{job_id}/result returned {response.status_code}: {result}"
            )

        quotes = result.get("quotes")
        if not isinstance(quotes, list) or not quotes:
            raise SmokeTestError(f"No quotes in the result: {result}")
        print(f"   received {len(quotes)} quotes")

        print("[2/3] Checking that an invalid URL fails gracefully")
        invalid_job_id = _create_job(client, api_url, INVALID_URL)
        print(f"   job_id: {invalid_job_id}")

        invalid_status = _wait_for_terminal_status(client, api_url, invalid_job_id)
        if invalid_status["status"] != "failed":
            raise SmokeTestError(
                f"Invalid URL job {invalid_job_id} did not fail: {invalid_status}"
            )

        error = invalid_status.get("error")
        if not isinstance(error, str) or not error:
            raise SmokeTestError(
                f"Invalid URL job {invalid_job_id} has no error message: {invalid_status}"
            )
        print(f"   error: {error}")

    print("[3/3] ✓ Smoke test passed")


def _resolve_api_url() -> str:
    if len(sys.argv) > 1:
        argument = sys.argv[1]
        if argument in {"-h", "--help"}:
            print("Usage: python scripts/smoke_test.py [API_URL]")
            raise SystemExit(0)
        return argument.rstrip("/")

    return os.getenv("API_URL", DEFAULT_API_URL).rstrip("/")


def main() -> int:
    api_url = _resolve_api_url()

    try:
        run(api_url)
    except SmokeTestError as exc:
        print(f"\n✗ Smoke test failed: {exc}", file=sys.stderr)
        return 1
    except httpx.HTTPError as exc:
        print(f"\n✗ HTTP error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n✗ Interrupted", file=sys.stderr)
        return 130
    except Exception as exc:  # noqa: BLE001 - report any unexpected failure
        print(f"\n✗ Unexpected error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
