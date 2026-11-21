"""Signed webhooks + async transcription jobs.

Outbound: POST /speech/jobs accepts audio and returns a job id immediately; when the transcript is ready
we POST it to the caller's `callback_url` (https + allowlisted host only) signed with HMAC-SHA256.
Inbound:  POST /speech/webhooks/{provider} lets an async-capable ASR provider (or Aditi's backend)
push a transcript into a job. Same signature scheme, with a timestamp to block replays.

Signature header:  X-VS-Signature: t=<unix>,v1=<hex hmac of "<t>." + raw body>
"""
from __future__ import annotations

import asyncio
import hmac
import hashlib
import json
import logging
import secrets
import time
from typing import Any, Awaitable, Callable
from urllib.parse import urlsplit

log = logging.getLogger(__name__)

SIGNATURE_HEADER = "X-VS-Signature"
TOLERANCE_SECONDS = 300


# ---- signing --------------------------------------------------------------------------------
def _mac(secret: str, timestamp: int, body: bytes) -> str:
    return hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()


def sign(secret: str, body: bytes, timestamp: int | None = None) -> str:
    t = int(time.time()) if timestamp is None else timestamp
    return f"t={t},v1={_mac(secret, t, body)}"


def verify(
    secret: str | None,
    header: str | None,
    body: bytes,
    tolerance: int = TOLERANCE_SECONDS,
    now: float | None = None,
) -> bool:
    if not secret or not header:
        return False
    parts = dict(p.split("=", 1) for p in header.split(",") if "=" in p)
    try:
        t = int(parts["t"])
        given = parts["v1"]
    except (KeyError, ValueError):
        return False
    if abs((time.time() if now is None else now) - t) > tolerance:
        return False  # stale or replayed
    return hmac.compare_digest(_mac(secret, t, body), given)


# ---- SSRF guard -----------------------------------------------------------------------------
def validate_callback_url(url: str, allowed_hosts: set[str]) -> str:
    """Only https URLs on an explicit host allowlist (prevents using the service to probe internal networks)."""
    parts = urlsplit(url)
    if parts.scheme != "https":
        raise ValueError("callback_url must use https")
    if parts.username or parts.password:
        raise ValueError("callback_url must not contain credentials")
    host = (parts.hostname or "").lower()
    if not host or host not in {h.lower() for h in allowed_hosts}:
        raise ValueError("callback_url host is not allowed")
    return url


# ---- job store ------------------------------------------------------------------------------
class JobStore:
    """In-memory store. Fine for one process; swap for Redis/Postgres when running several workers."""

    def __init__(self, ttl: float = 3600, max_jobs: int = 1000, clock: Callable[[], float] = time.time):
        self.ttl, self.max_jobs, self.clock = ttl, max_jobs, clock
        self._jobs: dict[str, dict[str, Any]] = {}

    def _gc(self) -> None:
        cutoff = self.clock() - self.ttl
        for k in [k for k, v in self._jobs.items() if v["created"] < cutoff]:
            del self._jobs[k]
        while len(self._jobs) >= self.max_jobs:  # drop oldest
            del self._jobs[min(self._jobs, key=lambda k: self._jobs[k]["created"])]

    def create(self) -> str:
        self._gc()
        job_id = secrets.token_urlsafe(16)
        self._jobs[job_id] = {"id": job_id, "status": "pending", "text": None, "engine": None, "error": None, "created": self.clock()}
        return job_id

    def get(self, job_id: str) -> dict[str, Any] | None:
        self._gc()
        return self._jobs.get(job_id)

    def update(self, job_id: str, **fields: Any) -> None:
        if job_id in self._jobs:
            self._jobs[job_id].update(fields)


# ---- outbound delivery ----------------------------------------------------------------------
async def deliver_callback(
    client: Any,
    url: str,
    payload: dict,
    secret: str,
    retries: int = 3,
    backoff: float = 0.5,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> bool:
    """POST a signed JSON payload. Retries 5xx/429/network errors with backoff; never retries other 4xx."""
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    for attempt in range(retries):
        headers = {"Content-Type": "application/json", SIGNATURE_HEADER: sign(secret, body)}
        try:
            r = await client.post(url, content=body, headers=headers)
            if r.status_code < 300:
                return True
            if 400 <= r.status_code < 500 and r.status_code != 429:
                log.warning("callback rejected with %s; not retrying", r.status_code)
                return False
        except Exception as e:
            log.info("callback attempt %d failed: %s", attempt + 1, e)
        if attempt < retries - 1:
            await sleep(backoff * (2**attempt))
    return False


async def run_job(
    job_id: str,
    store: JobStore,
    transcribe: Callable[[bytes, str, str], Awaitable[Any]],
    audio: bytes,
    filename: str,
    language: str,
    callback_url: str | None = None,
    secret: str | None = None,
    client_factory: Callable[[], Any] | None = None,
) -> None:
    """Transcribe in the background, record the result, then notify the callback (if any)."""
    try:
        r = await transcribe(audio, filename, language)
        store.update(job_id, status="done", text=r.text, engine=r.engine)
        payload = {"job_id": job_id, "status": "done", "text": r.text, "engine": r.engine}
    except Exception as e:
        log.warning("job %s failed: %s", job_id, e)
        store.update(job_id, status="failed", error="transcription failed")
        payload = {"job_id": job_id, "status": "failed"}

    if callback_url and secret and client_factory:
        client = client_factory()
        try:
            await deliver_callback(client, callback_url, payload, secret)
        finally:
            close = getattr(client, "aclose", None)
            if close:
                await close()
