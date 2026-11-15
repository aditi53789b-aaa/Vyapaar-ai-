"""FastAPI router for everything speech-related. Aditi mounts it in the main app:

    from speech.router import router as speech_router
    app.include_router(speech_router)

Environment
    SPEECH_API_KEY          shared secret for server-to-server calls (X-Internal-Key header)
    SPEECH_WS_SECRET        HMAC secret for live-stream tokens (same value as the Next.js app)
    SPEECH_WEBHOOK_SECRET   HMAC secret for signed webhooks (in and out)
    WEBHOOK_ALLOWED_HOSTS   comma-separated hosts that jobs may call back, e.g. "api.vyapaarsathi.in"
    ALLOWED_ORIGINS         comma-separated browser origins allowed on the WebSocket (recommended)
    SPEECH_ENV=dev          local development only: skips the key/token requirements
"""
from __future__ import annotations

import hmac
import json
import logging
import os

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Header, HTTPException, Request, UploadFile, WebSocket

from .pipeline import SpeechPipeline, TranscriptResult, normalise_text
from .stream import StreamingSession, StreamLimitExceeded
from .tokens import verify_token
from .webhooks import JobStore, run_job, validate_callback_url, verify

log = logging.getLogger(__name__)

router = APIRouter(prefix="/speech", tags=["speech"])
_pipeline = SpeechPipeline()
_jobs = JobStore()

MAX_BYTES = 10 * 1024 * 1024
MAX_WEBHOOK_BYTES = 64 * 1024
_DEV = lambda: os.getenv("SPEECH_ENV") == "dev"  # noqa: E731


def require_api_key(x_internal_key: str | None = Header(default=None)) -> None:
    expected = os.getenv("SPEECH_API_KEY")
    if not expected:
        if _DEV():
            return
        raise HTTPException(503, "SPEECH_API_KEY is not configured")
    if not x_internal_key or not hmac.compare_digest(x_internal_key, expected):
        raise HTTPException(401, "Unauthorized")


async def _read_audio(audio: UploadFile) -> bytes:
    data = await audio.read(MAX_BYTES + 1)
    if not data:
        raise HTTPException(400, "Empty audio")
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Audio too large")
    return data


# ---- one-shot transcription ----------------------------------------------------------------
@router.post("/transcribe", dependencies=[Depends(require_api_key)])
async def transcribe(audio: UploadFile = File(...), language: str = Form("hinglish")):
    data = await _read_audio(audio)
    try:
        r = await _pipeline.transcribe(data, audio.filename or "entry.webm", language)
    except RuntimeError as e:
        raise HTTPException(502, str(e))
    return {"text": r.text, "language": r.language, "engine": r.engine}


# ---- async jobs + signed webhooks ------------------------------------------------------------
def _allowed_hosts() -> set[str]:
    return {h.strip() for h in os.getenv("WEBHOOK_ALLOWED_HOSTS", "").split(",") if h.strip()}


def _http_client():
    import httpx

    return httpx.AsyncClient(timeout=10.0, follow_redirects=False)


@router.post("/jobs", status_code=202, dependencies=[Depends(require_api_key)])
async def create_job(
    background: BackgroundTasks,
    audio: UploadFile = File(...),
    language: str = Form("hinglish"),
    callback_url: str | None = Form(None),
):
    secret = os.getenv("SPEECH_WEBHOOK_SECRET")
    if callback_url:
        if not secret:
            raise HTTPException(503, "SPEECH_WEBHOOK_SECRET is not configured")
        try:
            validate_callback_url(callback_url, _allowed_hosts())
        except ValueError as e:
            raise HTTPException(400, str(e))
    data = await _read_audio(audio)
    job_id = _jobs.create()
    background.add_task(
        run_job, job_id, _jobs, _pipeline.transcribe, data, audio.filename or "entry.webm", language,
        callback_url, secret, _http_client,
    )
    return {"job_id": job_id, "status": "pending"}


@router.get("/jobs/{job_id}", dependencies=[Depends(require_api_key)])
async def get_job(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Unknown job")
    return {k: job[k] for k in ("id", "status", "text", "engine", "error")}


@router.post("/webhooks/{provider}")
async def inbound_webhook(provider: str, request: Request, x_vs_signature: str | None = Header(default=None)):
    """Signed push of a finished transcript into a job (async ASR providers, or other Vyapaar services)."""
    if provider not in {"bhashini", "whisper", "custom"}:
        raise HTTPException(404, "Unknown provider")
    secret = os.getenv("SPEECH_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(503, "SPEECH_WEBHOOK_SECRET is not configured")
    body = await request.body()
    if len(body) > MAX_WEBHOOK_BYTES:
        raise HTTPException(413, "Payload too large")
    if not verify(secret, x_vs_signature, body):
        raise HTTPException(401, "Bad signature")
    try:
        data = json.loads(body)
        job_id, text = str(data["job_id"]), str(data["text"])
    except (ValueError, KeyError, TypeError):
        raise HTTPException(400, "Expected JSON with job_id and text")
    if not _jobs.get(job_id):
        raise HTTPException(404, "Unknown job")
    _jobs.update(job_id, status="done", text=normalise_text(text), engine=provider)
    return {"ok": True}


# ---- live streaming ---------------------------------------------------------------------------
async def _final(audio: bytes, filename: str, language: str) -> tuple[str, str]:
    r: TranscriptResult = await _pipeline.transcribe(audio, filename, language)
    return r.text, r.engine


@router.websocket("/stream")
async def stream(ws: WebSocket, token: str | None = None):
    """Protocol: text {"type":"start","language":"hi","mime":"audio/webm"} -> binary chunks -> text {"type":"stop"}.
    Server replies {"type":"partial","text"} (repeatedly), then {"type":"final","text","engine"}."""
    origins = {o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()}
    if origins and ws.headers.get("origin") not in origins:
        await ws.close(code=4403)
        return
    secret = os.getenv("SPEECH_WS_SECRET")
    if not (verify_token(token, secret) or (_DEV() and not secret)):
        await ws.close(code=4401)
        return
    await ws.accept()

    session: StreamingSession | None = None

    def new_session(language: str = "hinglish", mime: str = "") -> StreamingSession:
        return StreamingSession(
            transcribe_partial=_pipeline.transcribe_fast,
            transcribe_final=_final,
            emit=ws.send_json,
            language=language,
            mime=mime,
        )

    try:
        while True:
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect":
                break
            if msg.get("text") is not None:
                try:
                    data = json.loads(msg["text"])
                except ValueError:
                    continue
                if data.get("type") == "start" and session is None:
                    session = new_session(str(data.get("language") or "hinglish")[:20], str(data.get("mime") or "")[:60])
                elif data.get("type") == "stop":
                    if session is not None:
                        await session.finish()
                    break
            elif msg.get("bytes") is not None:
                if session is None:
                    session = new_session()
                await session.feed(msg["bytes"])
    except StreamLimitExceeded:
        await ws.send_json({"type": "error", "message": "recording too long"})
    except Exception:
        log.exception("stream error")
    finally:
        if session is not None:
            await session.close()
        try:
            await ws.close()
        except Exception:
            pass
