"""Streaming ("Whisper Streaming"-style) transcription session.

The browser sends MediaRecorder chunks (every ~250 ms). Chunks of one recording concatenate into a
valid webm/mp4 file, so every ~1.5 s we transcribe the audio received *so far* and emit a
{"type": "partial"} message; on stop we transcribe the full clip once more with the best engine
(Bhashini for Indic languages) and emit {"type": "final"}.

Framework-agnostic on purpose (takes `emit` and the transcribe callables) so it is unit-testable
without FastAPI; router.py wires it to a WebSocket.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Awaitable, Callable

log = logging.getLogger(__name__)

PartialFn = Callable[[bytes, str, str], Awaitable[str]]  # (audio, filename, language) -> text
FinalFn = Callable[[bytes, str, str], Awaitable[tuple[str, str]]]  # -> (text, engine)
EmitFn = Callable[[dict], Awaitable[None]]


class StreamLimitExceeded(Exception):
    pass


class StreamingSession:
    def __init__(
        self,
        *,
        transcribe_partial: PartialFn,
        transcribe_final: FinalFn,
        emit: EmitFn,
        language: str = "hinglish",
        mime: str = "",
        partial_interval: float = 1.5,
        min_bytes: int = 6_000,
        max_bytes: int = 5 * 1024 * 1024,
        max_seconds: float = 35.0,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.transcribe_partial = transcribe_partial
        self.transcribe_final = transcribe_final
        self.emit = emit
        self.language = (language or "hinglish").lower()
        self.partial_interval = partial_interval
        self.min_bytes = min_bytes
        self.max_bytes = max_bytes
        self.max_seconds = max_seconds
        self.clock = clock
        self.filename = "stream.m4a" if "mp4" in mime else "stream.webm"

        self._buf = bytearray()
        self._started = clock()
        self._last_partial = float("-inf")
        self._last_text = ""
        self._task: asyncio.Task | None = None
        self._finished = False

    async def feed(self, chunk: bytes) -> None:
        if self._finished or not chunk:
            return
        self._buf.extend(chunk)
        if len(self._buf) > self.max_bytes or self.clock() - self._started > self.max_seconds:
            raise StreamLimitExceeded("recording too long")
        self._maybe_start_partial()

    def _maybe_start_partial(self) -> None:
        if self._task is not None and not self._task.done():
            return  # at most one partial in flight
        if len(self._buf) < self.min_bytes:
            return
        if self.clock() - self._last_partial < self.partial_interval:
            return
        self._last_partial = self.clock()
        self._task = asyncio.create_task(self._run_partial(bytes(self._buf)))

    async def _run_partial(self, snapshot: bytes) -> None:
        try:
            text = await self.transcribe_partial(snapshot, self.filename, self.language)
        except Exception as e:  # partials are best-effort; the final pass decides
            log.info("partial transcription skipped: %s", e)
            return
        if self._finished or not text or text == self._last_text:
            return
        self._last_text = text
        await self.emit({"type": "partial", "text": text})

    async def finish(self) -> str:
        self._finished = True
        await self._cancel_partial()
        if not self._buf:
            await self.emit({"type": "final", "text": "", "engine": "none"})
            return ""
        try:
            text, engine = await self.transcribe_final(bytes(self._buf), self.filename, self.language)
        except Exception as e:
            log.warning("final transcription failed: %s", e)
            await self.emit({"type": "error", "message": "transcription failed"})
            return ""
        await self.emit({"type": "final", "text": text, "engine": engine})
        return text

    async def _cancel_partial(self) -> None:
        task, self._task = self._task, None
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass

    async def close(self) -> None:
        self._finished = True
        await self._cancel_partial()
